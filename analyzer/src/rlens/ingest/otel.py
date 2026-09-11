"""OTEL / OpenInference span tree -> the raw materials for segmentation. C3.1, C3.2.

Owner: M1-0 skeleton · **implemented by M1-8**. C3.2 assigns this to M1-6; M1-6 built the
emission side and left this a skeleton, so the segmenter inherited it — the segmenter
cannot be byte-stable over an input that does not exist.

The mapping is ADR-002 §1's, taken from what S2 **observed** rather than what C3.1 hoped:

  * The live namespace is OpenInference `llm.*` / `openinference.*`. **No `gen_ai.*`
    attribute arrives at all** — five of C3.1's nine rows named one and all five were dead.
  * **Reasoning text does not reach a third-party span tree.** LangChain drops the
    runtime's `reasoning` field before the instrumentor sees it, so our runner writes
    `llm.output_messages.0.message.reasoning` itself. A tree without it degrades to
    `trace_quality: "partial"` — it does not error, and that is what lets the analyzer run
    against a stock LangGraph capture at all (B12).
  * Tool results arrive as `output.value` on the TOOL span; the capture has **zero span
    events**, so nothing here reads events.

This module is one of the two places provider payload shapes may appear (C2.2). It reads
attribute names, never a provider SDK.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from rlens.checkers import final_answer_line
from rlens.contracts import Strategy, Timings, TraceQuality, Usage

#: Ours. Present on trees the runner emitted, absent on everybody else's.
NS = "rlens"

KIND = "openinference.span.kind"


class IngestError(ValueError):
    """The tree is not a tree. A malformed input, not a degraded one."""


@dataclass
class LlmCall:
    """One LLM span: the thought text it produced, and where it sits in the loop."""

    span_id: str
    reasoning: str
    content: str
    seq: int
    turn: int
    reasoning_tokens: int | None = None
    answer_tokens: int | None = None


@dataclass
class ToolUse:
    """One TOOL span: the call and the observation, already paired by the emitter."""

    span_id: str
    name: str
    arguments: str
    observation: str
    ok: bool | None
    seq: int
    turn: int


@dataclass
class ParsedTrace:
    """Everything the segmenter needs, and nothing it does not.

    Deliberately **not** a half-built `NormalizedTrace`. A `NormalizedTrace` with
    `steps=[]` would be a valid object asserting that a trace has no steps, and it would be
    passed around as though segmentation had happened. This type cannot be mistaken for a
    finished trace.
    """

    strategy: Strategy
    item_id: str
    calls: list[LlmCall] = field(default_factory=list)
    tools: list[ToolUse] = field(default_factory=list)
    trace_quality: TraceQuality = "full"
    model_pin: str = ""
    usage: Usage = field(default_factory=Usage)
    timings: Timings = field(default_factory=Timings)

    @property
    def final_answer_source(self) -> str:
        """The last LLM span's visible content. The answer is what the model *said*.

        Not the last non-empty content: on a ReAct trace the tool-calling turns have empty
        content by construction (ADR-007), and the answer is the final turn's. Reaching
        back past an empty final turn would pick up a mid-loop remark and present it as the
        answer.
        """
        return self.calls[-1].content if self.calls else ""


def _spans(tree: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans = tree.get("resourceSpans") if isinstance(tree, dict) else tree
    if not isinstance(spans, list) or not spans:
        raise IngestError("no spans: expected {'resourceSpans': [...]} or a list of spans")
    return spans


def _seq(span: dict[str, Any], fallback: int) -> int:
    """Execution order. `rlens.seq` when we emitted the tree, list order otherwise.

    A serialised tree carries no timestamps, and `step_id` embeds an ordinal — so order has
    to come from somewhere explicit. Ours carries it; a third-party tree does not, and its
    export order is the only ordering information it has. Sorting by span id would work
    until turn 10 sorted before turn 2.
    """
    value = span.get("attributes", {}).get(f"{NS}.seq")
    return int(value) if isinstance(value, int) else fallback


def parse(
    tree: dict[str, Any] | list[dict[str, Any]], *, strategy: Strategy | None = None
) -> ParsedTrace:
    """Read a span tree into the segmenter's input.

    `strategy` is normally read off the root span. It is overridable because a third-party
    tree has no `rlens.strategy` attribute — B12's stock LangGraph capture is a ReAct agent
    and the caller is the only one who can say so.
    """
    spans = _spans(tree)
    by_kind: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for i, span in enumerate(spans):
        attrs = span.get("attributes") or {}
        by_kind.setdefault(str(attrs.get(KIND, "")), []).append((i, span))

    roots = by_kind.get("CHAIN", [])
    root_attrs: dict[str, Any] = {}
    for _, span in roots:
        # OUR root is the one carrying the strategy. A third-party tree has several CHAIN
        # spans (the S2 capture has five) and none of them is ours, so the first CHAIN is
        # not a safe answer.
        if f"{NS}.strategy" in (span.get("attributes") or {}):
            root_attrs = span["attributes"]
            break

    resolved = strategy or root_attrs.get(f"{NS}.strategy")
    if resolved not in ("direct", "thinking", "react"):
        raise IngestError(
            f"cannot determine the strategy (found {resolved!r}). Our trees carry "
            f"`{NS}.strategy` on the root CHAIN span; for a third-party tree, pass "
            f"`strategy=` explicitly."
        )

    calls: list[LlmCall] = []
    for i, span in by_kind.get("LLM", []):
        attrs = span.get("attributes") or {}
        calls.append(
            LlmCall(
                span_id=str(span.get("spanId") or f"llm-{i}"),
                reasoning=str(attrs.get("llm.output_messages.0.message.reasoning") or ""),
                content=str(attrs.get("llm.output_messages.0.message.content") or ""),
                seq=_seq(span, i),
                turn=int(attrs.get(f"{NS}.turn") or 0),
                reasoning_tokens=attrs.get(f"{NS}.token_count.reasoning"),
                answer_tokens=attrs.get(f"{NS}.token_count.answer"),
            )
        )
    calls.sort(key=lambda c: c.seq)

    tools: list[ToolUse] = []
    for i, span in by_kind.get("TOOL", []):
        attrs = span.get("attributes") or {}
        tools.append(
            ToolUse(
                span_id=str(span.get("spanId") or f"tool-{i}"),
                name=str(attrs.get("tool.name") or span.get("name") or "tool"),
                arguments=_tool_arguments(attrs),
                observation=str(attrs.get("output.value") or ""),
                ok=attrs.get(f"{NS}.tool.ok"),
                seq=_seq(span, i),
                turn=int(attrs.get(f"{NS}.turn") or 0),
            )
        )
    tools.sort(key=lambda t: t.seq)

    quality = str(root_attrs.get(f"{NS}.trace_quality") or "")
    if quality not in ("full", "partial", "provider_summarised"):
        # A tree that does not say is a tree we did not emit. If it has no reasoning text
        # either, it is genuinely partial -- that is ADR-002's degradation path, and it is
        # what lets the analyzer ingest a stock LangGraph capture rather than reject it.
        #
        # The answer half has to be checked too, and by the SAME rule the runner uses, or
        # our trees and a third-party tree would get different verdicts from the same
        # evidence.
        answered = bool(calls and final_answer_line(calls[-1].content))
        quality = "full" if any(c.reasoning for c in calls) and answered else "partial"

    return ParsedTrace(
        strategy=resolved,
        item_id=str(root_attrs.get(f"{NS}.item_id") or ""),
        calls=calls,
        tools=tools,
        trace_quality=quality,  # type: ignore[arg-type]
        model_pin=str(root_attrs.get(f"{NS}.pin.fingerprint") or ""),
        usage=_usage(calls, by_kind.get("LLM", [])),
        timings=Timings(turns=len(calls) or None),
    )


def _tool_arguments(attrs: dict[str, Any]) -> str:
    """The call's arguments. `input.value` is the name the reference capture uses.

    S2 also found tool-call arguments on the *calling LLM span* in a stock trace. Ours are
    on the TOOL span, where the reference capture puts its `input.value`, so one read
    serves both -- see ADR-007.
    """
    raw = attrs.get("input.value")
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, sort_keys=True)


def _usage(calls: list[LlmCall], llm_spans: list[tuple[int, dict[str, Any]]]) -> Usage:
    """Summed across turns. **Arm 3's cost is the whole loop, not its last turn** (ADR-007).

    A three-turn agent reported by its final turn understates its cost by most of it.
    """
    reasoning = [c.reasoning_tokens for c in calls if c.reasoning_tokens is not None]
    answer = [c.answer_tokens for c in calls if c.answer_tokens is not None]
    tokenizer = None
    input_tokens = output_tokens = 0
    for _, span in llm_spans:
        attrs = span.get("attributes") or {}
        input_tokens += int(attrs.get("llm.token_count.prompt") or 0)
        output_tokens += int(attrs.get("llm.token_count.completion") or 0)
        tokenizer = tokenizer or attrs.get(f"{NS}.tokenizer")
    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        # None rather than 0 when nothing reported a count: 0 reasoning tokens is a real
        # and different claim from "we do not know".
        reasoning_tokens=sum(reasoning) if reasoning else None,
        answer_tokens=sum(answer) if answer else None,
        tokenizer=tokenizer,
    )
