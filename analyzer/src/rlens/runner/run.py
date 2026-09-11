"""Executing the arms. C4.1's concurrency, timeout and failure semantics.

Owner: M1-6.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any

from rlens.checkers import final_answer_line
from rlens.llm import Completion, ProviderError, generate
from rlens.runner.arms import ARMS, ArmSpec, messages_for
from rlens.runner.emit import arm_span_attributes, llm_span_attributes
from rlens.runner.paths import data_path, missing_data_message
from rlens.runner.react import ReactResult, build_react_spans, run_react
from rlens.versions import GenerationPin, generation_pin


@dataclass
class ArmResult:
    """One arm's outcome. `failed` and `partial` are first-class, not exceptions.

    C4.1/B6.5: a failed arm must not take the run down -- the other arms still render,
    and the UI shows a failed column. An arm that raised out of here would make a
    provider hiccup on one arm delete the two good traces beside it.
    """

    strategy: str
    item_id: str
    trace_quality: str  # full | partial | provider_summarised
    completion: Completion | None = None
    failed_reason: str | None = None
    spans: list[dict[str, Any]] = field(default_factory=list)
    #: Arm 3 only. The loop's full record -- turns, tool invocations, whether `max_turns`
    #: bound. Present on the result rather than only in the spans because the CLI reports
    #: it and M1-9's metrics will read it, and re-deriving "how many tools were called"
    #: by filtering a span tree is a re-derivation of something already known.
    react: ReactResult | None = None

    @property
    def ok(self) -> bool:
        return self.completion is not None

    @property
    def final_answer(self) -> str:
        """C4.1's arms both ask for the answer on its own last line -- and the model does
        not always oblige. The rule lives in `rlens.checkers` so the segmenter and the
        measurement harnesses read answers exactly the way the runner reports them."""
        if not self.completion:
            return ""
        return final_answer_line(self.completion.text)


async def run_arm(
    spec: ArmSpec,
    item_id: str,
    prompt: str,
    *,
    pin: GenerationPin | None = None,
    timeout: float | None = None,
    cassette: str | None = None,
) -> ArmResult:
    """Run one arm to a result. Never raises for a provider or timeout failure."""
    pin = pin or generation_pin()
    timeout = timeout if timeout is not None else float(os.environ.get("ARM_TIMEOUT_S", "180"))
    if spec.strategy == "react":
        return await _run_react_arm(
            spec, item_id, prompt, pin=pin, timeout=timeout, cassette=cassette
        )
    messages = messages_for(spec, prompt)
    cassette = cassette or f"{item_id}.{spec.strategy}"

    try:
        completion = await asyncio.wait_for(
            asyncio.to_thread(
                generate,
                messages,
                pin=pin,
                thinking=spec.thinking,
                reasoning_effort=spec.reasoning_effort,
                cassette=cassette,
            ),
            timeout=timeout,
        )
    except TimeoutError:
        # C4.1: a timed-out arm emits a PARTIAL trace, it does not fail the run. There is
        # nothing partial to emit here because the call is not streamed -- so the honest
        # encoding is a partial trace with no steps, not a full trace with none.
        return ArmResult(
            strategy=spec.strategy,
            item_id=item_id,
            trace_quality="partial",
            failed_reason=f"timeout after {timeout:g}s",
        )
    except ProviderError as exc:
        return ArmResult(
            strategy=spec.strategy,
            item_id=item_id,
            trace_quality="partial",
            failed_reason=str(exc),
        )

    # An arm that asked for thinking and got none is NOT a full trace. Saying "full"
    # here would put an empty reasoning panel in front of a reviewer with nothing
    # marking it as degraded, which is exactly the failure C3.1's rule exists to prevent.
    #
    # **And the mirror case is just as real, which M1-8 found by segmenting the corpus.**
    # `mb-08.thinking` produced 141 reasoning steps and an EMPTY `content`: the model
    # looped 126 times on a fact that does not exist and never answered. Reasoning was
    # present, so the old rule called that trace `full`. It is not -- there is no answer
    # in it. Downstream that would be recorded as `correct: false`, i.e. the model
    # answered and was wrong, when the model never answered at all. It is the same
    # distinction M1-5 had to draw between `unparsed` and `wrong`, one layer up.
    quality = "full"
    if (spec.thinking and not completion.reasoning) or not final_answer_line(completion.text):
        quality = "partial"

    result = ArmResult(
        strategy=spec.strategy,
        item_id=item_id,
        trace_quality=quality,
        completion=completion,
    )
    result.spans = _build_spans(result, spec, messages, pin)
    return result


async def _run_react_arm(
    spec: ArmSpec,
    item_id: str,
    prompt: str,
    *,
    pin: GenerationPin,
    timeout: float,
    cassette: str | None,
) -> ArmResult:
    """Arm 3. One timeout for the WHOLE loop, not per turn.

    Per-turn timeouts would let a stuck agent spend `max_turns x ARM_TIMEOUT_S` -- 18
    minutes at the committed settings -- while every individual turn looked healthy. C4.1
    budgets the arm, so the arm is what is bounded.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_react,
                item_id,
                prompt,
                pin=pin,
                cassette_prefix=cassette,
            ),
            timeout=timeout,
        )
    except TimeoutError:
        return ArmResult(
            strategy=spec.strategy,
            item_id=item_id,
            trace_quality="partial",
            failed_reason=f"timeout after {timeout:g}s",
        )

    if result.failed_reason is not None and not result.turns:
        # The provider failed on turn 0: there is no trace at all. Other arms still render.
        return ArmResult(
            strategy=spec.strategy,
            item_id=item_id,
            trace_quality="partial",
            failed_reason=result.failed_reason,
            react=result,
        )

    # `partial` covers three distinct shapes, and all three are genuinely incomplete
    # traces rather than failures: the loop ran out of turns, the provider died mid-loop
    # after some turns succeeded, or the model asked to think and returned nothing.
    final = result.final
    degraded = (
        result.max_turns_exhausted
        or result.failed_reason is not None
        or (final is not None and not final.reasoning)
        # A loop that ended without a visible answer is a partial trace, same as above.
        or (final is not None and not final_answer_line(final.text))
    )
    quality = "partial" if degraded else "full"

    arm = ArmResult(
        strategy=spec.strategy,
        item_id=item_id,
        trace_quality=quality,
        completion=final,
        failed_reason=result.failed_reason,
        react=result,
    )
    arm.spans = build_react_spans(result, item_id, pin, trace_quality=quality)
    return arm


def _build_spans(
    result: ArmResult, spec: ArmSpec, messages: list[dict[str, str]], pin: GenerationPin
) -> list[dict[str, Any]]:
    """The arm's span tree as plain dicts: one root CHAIN, one child LLM span.

    Dicts rather than SDK objects so the runner's output is exactly what the analyzer
    ingests -- a serialised tree -- with no in-process shortcut that would let the two
    diverge. `emit.build_tracer_provider` writes the same attributes through the real SDK
    when a run is exported to Langfuse.
    """
    assert result.completion is not None
    # **The item id is IN the span id, and that is a correctness fix, not decoration.**
    # `step_id` is `{strategy}:{span_id}:{ordinal}` and C3.2 calls it the join key for
    # every label ever written. Without the item id, `direct:direct-llm-0:0` named the
    # first step of all 14 items at once -- 310 steps collapsed to 155 distinct ids, and
    # any code building a dict keyed by step_id across traces silently lost half of them.
    # M1-11's sampling draw hit it on its first run, before a single label existed.
    #
    # Still fully deterministic: regenerating a tree from its cassette yields the same
    # ids, which is what makes the segmenter goldens and cassette replay reproducible. A
    # random id would have bought uniqueness by giving that up.
    root_id = f"{spec.strategy}-{result.item_id}-root"
    return [
        {
            "name": f"arm.{spec.strategy}",
            "spanId": root_id,
            "parentSpanId": None,
            "attributes": arm_span_attributes(
                spec.strategy,
                result.item_id,
                pin,
                deterministic=spec.deterministic,
                trace_quality=result.trace_quality,
                failed_reason=result.failed_reason,
            ),
            "events": [],
        },
        {
            "name": "llm.generate",
            "spanId": f"{root_id}-llm-0",
            "parentSpanId": root_id,
            "attributes": llm_span_attributes(result.completion, messages, pin),
            "events": [],
        },
    ]


async def run_arms(
    item_id: str,
    prompt: str,
    strategies: list[str],
    *,
    pin: GenerationPin | None = None,
) -> list[ArmResult]:
    """All requested arms concurrently (C4.1: `asyncio.gather`), each with its own timeout."""
    pin = pin or generation_pin()
    return list(
        await asyncio.gather(*(run_arm(ARMS[s], item_id, prompt, pin=pin) for s in strategies))
    )


def load_item(item_id: str, bank_dir: str | None = None) -> dict[str, Any]:
    """Read a bank item as DATA from `problem-bank/items/`.

    Read, never imported. `.importlinter`'s I1 contract forbids `rlens` importing
    `problem_bank`, and it is right to: the analyzer package must not acquire a
    dependency on the corpus it happens to be pointed at. A path and `json.load` keep
    the bank a runtime input.

    The bank itself is M1-4 (W2-c), after this task -- so the CLI also takes `--prompt`,
    and this raises a message saying which task owns the gap rather than a bare KeyError.
    """
    root = (
        pathlib.Path(bank_dir)
        if bank_dir
        else data_path("problem-bank/items", env_var="PROBLEM_BANK_DIR")
    )
    path = root / f"{item_id}.json"
    if not path.exists():
        where = missing_data_message("problem-bank/items", "PROBLEM_BANK_DIR")
        raise FileNotFoundError(f"No bank item at {path}. {where}")
    item: dict[str, Any] = json.loads(path.read_text())
    return item


#: Below this ratio of direct-arm to thinking-arm reasoning tokens, the two regimes are
#: considered separated. Arm 1 at `low` measured ~4% of arm 2 on the probe; 0.5 leaves
#: wide room for problem-to-problem variance while still catching a collapse.
REGIME_SEPARATION_MAX_RATIO = 0.5


def check_regime_separation(results: list[ArmResult]) -> str | None:
    """Did the arms actually run in different regimes? Returns a warning, or None.

    **This exists because the provider lies.** S7 found that `reasoning_effort: "none"`
    and ollama's native `think: false` are both silently ignored by gpt-oss:20b -- the
    request is accepted, nothing errors, and a full trace comes back. A runner that
    trusted the parameter would publish a "minimal-reasoning baseline" that had reasoned
    just as hard as the arm it is the baseline FOR, and every cost-of-thought number
    downstream would be wrong with nothing visibly broken.

    So the regime is checked against the OUTPUT, not the request. This is the same
    principle as S1 gating G0 on a token ratio rather than on "thinking text: present".
    """
    by = {r.strategy: r for r in results if r.ok and r.completion is not None}
    direct, thinking = by.get("direct"), by.get("thinking")
    if not direct or not thinking:
        return None
    assert direct.completion is not None and thinking.completion is not None
    d, t = direct.completion.reasoning_tokens, thinking.completion.reasoning_tokens
    if d is None or t is None:
        return "regime separation UNVERIFIED: no token count (unknown tokenizer)"
    if t == 0:
        return "regime separation UNVERIFIED: the thinking arm produced no reasoning"
    ratio = d / t
    if ratio > REGIME_SEPARATION_MAX_RATIO:
        return (
            f"REGIME COLLAPSE: the direct arm reasoned {d} tokens against the thinking "
            f"arm's {t} ({ratio:.0%}). The arms are not in different regimes, so "
            f"cost-of-thought is not measurable from this run. See ADR-004."
        )
    return None
