"""Arm 3 — the ReAct loop. C4.1, `max_turns = 6`, `calculator` + `lookup`.

Owner: M1-7.

**Why this is not LangGraph, when C4.1 says "LangGraph ReAct loop"** — see
`docs/decisions/ADR-007-react-arm-on-the-provider-layer.md`. In one line: on a tool-calling
turn this model returns an *empty* `content` and puts the entire thought in the `reasoning`
field, and S2 established that `langchain_openai.ChatOpenAI` drops `reasoning` before any
instrumentation sees it. A LangGraph arm 3 would therefore emit a ReAct trace with **no
thought text at all**, and C4.2's ReAct segmentation is defined as "the thought text
preceding each TOOL span becomes one `thought` step". The arm whose traces are the most
structurally interesting would arrive with its reasoning panel blank.

B12's "integration, not a rewrite" evidence does not depend on this arm: it is
`test_third_party_spans.py` running the analyzer against the stock LangGraph capture S2
committed, and that test is green. What arm 3 owes the project is a *conforming trace*, and
it is emitted here through the same `llm.py` and the same `emit.py` as arms 1 and 2.

The loop, and the three things that can go wrong
------------------------------------------------
Each turn: ask the model, and if it asked for tools, run them and feed the observations
back. Terminate when it answers without calling a tool. Three failure modes are first-class
rather than exceptional, because each of them is a *result* about the arm:

* **`max_turns` exhausted** — the loop stops and the trace is `partial`. Not a failed run:
  an agent that cannot finish in 6 turns is an observation about the agent, and C4.1 wants
  the partial trace rather than nothing.
* **A bad tool call** — a name we do not have, a missing argument, unparseable JSON
  arguments. The observation says so and the loop continues; the model usually recovers on
  the next turn, which is the entire point of feeding errors back rather than raising.
* **No tool ever called** — legitimate on an `easy` item, where a ReAct loop has nothing
  useful to do. C4.1's DoD is explicit that arm 3 must run on those too and terminate
  *without burning turns*, so this terminates on the first turn like any other answer.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from rlens.llm import Completion, ProviderError, generate
from rlens.runner.arms import REACT_SYSTEM
from rlens.runner.emit import arm_span_attributes, llm_span_attributes, tool_span_attributes
from rlens.runner.tools import call_tool, load_corpus, tool_descriptions, tool_schemas
from rlens.versions import GenerationPin

#: C4.1. A turn is one model call plus the tool calls it requested.
MAX_TURNS_DEFAULT = 6


@dataclass
class ToolInvocation:
    """One executed tool call, kept so the span tree and the metrics read one record.

    `description` is captured at call time rather than looked up when the spans are built.
    The `lookup` description enumerates the corpus keys, so it is a function of the corpus
    that was actually in play — rebuilding it later would risk describing the call with a
    contract it was not made under.
    """

    turn: int
    name: str
    description: str
    arguments: dict[str, Any]
    observation: str
    ok: bool


@dataclass
class Turn:
    """One model call: what it was asked, and what came back.

    The request messages are kept because the LLM span carries them for arms 1 and 2, and
    an arm-3 LLM span with an empty input would be the only span in the system that lies
    about having had a prompt.
    """

    messages: list[dict[str, Any]]
    completion: Completion


@dataclass
class ReactResult:
    """Arm 3's outcome."""

    turns: list[Turn] = field(default_factory=list)
    invocations: list[ToolInvocation] = field(default_factory=list)
    max_turns: int = MAX_TURNS_DEFAULT
    max_turns_exhausted: bool = False
    failed_reason: str | None = None

    @property
    def final(self) -> Completion | None:
        return self.turns[-1].completion if self.turns else None

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def tool_calls_made(self) -> int:
        return len(self.invocations)

    @property
    def failed_tool_calls(self) -> int:
        return sum(1 for i in self.invocations if not i.ok)


def _assistant_message(comp: Completion) -> dict[str, Any]:
    """The assistant turn, in the shape the next request needs it.

    The `tool_calls` must go back in wire shape or the runtime cannot match the `tool`
    messages to them, and `arguments` must be re-serialised because `llm.py` parsed it on
    the way in. That round trip is deliberate: the parsed form is what the tools and the
    spans consume, and one module knowing the wire shape is the C2.2 rule working.
    """
    msg: dict[str, Any] = {"role": "assistant", "content": comp.text or ""}
    if comp.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"], sort_keys=True),
                },
            }
            for tc in comp.tool_calls
        ]
    return msg


def run_react(
    item_id: str,
    prompt: str,
    *,
    pin: GenerationPin,
    max_turns: int | None = None,
    corpus: dict[str, str] | None = None,
    cassette_prefix: str | None = None,
) -> ReactResult:
    """Run the loop to an answer, to `max_turns`, or to a provider failure."""
    limit = max_turns or int(os.environ.get("REACT_MAX_TURNS", MAX_TURNS_DEFAULT))
    facts = corpus if corpus is not None else load_corpus()
    schemas = tool_schemas(facts)
    descriptions = tool_descriptions(facts)
    prefix = cassette_prefix or f"{item_id}.react"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    result = ReactResult(max_turns=limit)

    for turn in range(limit):
        try:
            comp = generate(
                messages,
                pin=pin,
                thinking=True,
                reasoning_effort=None,
                tools=schemas,
                # One cassette per TURN. A single cassette for the arm could only replay
                # the first call, and the loop would then answer its own second turn with
                # its first turn's response — a green test replaying a conversation that
                # never happened.
                cassette=f"{prefix}.t{turn}",
            )
        except ProviderError as exc:
            result.failed_reason = str(exc)
            return result

        result.turns.append(Turn(messages=list(messages), completion=comp))

        if not comp.tool_calls:
            # Answered without calling a tool. The ONLY clean termination, and also the
            # `easy`-item path C4.1's DoD asks about: no tool needed, no turns burned.
            return result

        messages.append(_assistant_message(comp))
        for tc in comp.tool_calls:
            observation, ok = call_tool(tc["name"], tc["arguments"], facts)
            result.invocations.append(
                ToolInvocation(
                    turn=turn,
                    name=tc["name"],
                    description=descriptions.get(tc["name"], ""),
                    arguments=tc["arguments"],
                    observation=observation,
                    ok=ok,
                )
            )
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": observation})

    # Fell out of the loop still calling tools. C4.1: a partial trace, not a failed run.
    result.max_turns_exhausted = True
    return result


def build_react_spans(
    result: ReactResult,
    item_id: str,
    pin: GenerationPin,
    *,
    trace_quality: str,
) -> list[dict[str, Any]]:
    """The arm's span tree: one root CHAIN, an LLM span per turn, a TOOL span per call.

    TOOL spans are **siblings** of the LLM spans under the root, not children of the LLM
    span that requested them. That is what the stock LangGraph capture does — its tool
    spans hang off the graph, not off `ChatOpenAI` — and matching it keeps one segmenter
    path for our trees and third-party trees alike.

    Ordering is carried by `rlens.seq`, never by list position or span id: see
    `emit.tool_span_attributes`.
    """
    # See `run._arm_spans` for why the item id belongs in the span id: without it,
    # `step_id` is not unique across the corpus and it is C3.2's label join key.
    root_id = f"react-{item_id}-root"
    spans: list[dict[str, Any]] = [
        {
            "name": "arm.react",
            "spanId": root_id,
            "parentSpanId": None,
            "attributes": {
                **arm_span_attributes(
                    "react",
                    item_id,
                    pin,
                    deterministic=False,
                    trace_quality=trace_quality,
                    failed_reason=result.failed_reason,
                ),
                "rlens.react.turns": result.turn_count,
                "rlens.react.max_turns": result.max_turns,
                "rlens.react.max_turns_exhausted": result.max_turns_exhausted,
                "rlens.react.tool_calls": result.tool_calls_made,
                "rlens.react.failed_tool_calls": result.failed_tool_calls,
            },
            "events": [],
        }
    ]

    seq = 0
    for turn_index, turn in enumerate(result.turns):
        spans.append(
            {
                "name": "llm.generate",
                "spanId": f"{root_id}-llm-{turn_index}",
                "parentSpanId": root_id,
                "attributes": {
                    **llm_span_attributes(turn.completion, turn.messages, pin),
                    "rlens.turn": turn_index,
                    "rlens.seq": seq,
                },
                "events": [],
            }
        )
        seq += 1
        for i, inv in enumerate(x for x in result.invocations if x.turn == turn_index):
            spans.append(
                {
                    "name": inv.name,
                    "spanId": f"{root_id}-tool-{turn_index}-{i}",
                    "parentSpanId": root_id,
                    "attributes": tool_span_attributes(
                        inv.name,
                        inv.description,
                        inv.arguments,
                        inv.observation,
                        ok=inv.ok,
                        turn=turn_index,
                        seq=seq,
                    ),
                    "events": [],
                }
            )
            seq += 1
    return spans
