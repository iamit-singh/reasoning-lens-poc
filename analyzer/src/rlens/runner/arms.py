"""The strategy arms. C4.1, all three.

The arms exist to be *compared*, and everything that differs between them is a
confound unless it is the thing under study. So they share one model by construction
(ADR-001's same-model rule), one pin, one item, and one emission path. What differs is
the regime: whether the model thinks, and what the system prompt permits.

Owner: M1-6 (arms 1-2) · M1-7 (arm 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Strategy = Literal["direct", "thinking", "react"]

#: Arm 1 is the **cost-of-thought baseline, not an accuracy foil** (Revision Log #5).
#: It is a MINIMAL-reasoning baseline, not a zero-reasoning one -- see `DIRECT_EFFORT`
#: and ADR-004. The prompt still forbids showing work, which is what keeps the two arms'
#: *visible* output comparable; the hidden trace is what ADR-004 is about.
#: The distinction is what the prompt has to encode: the arm must answer as well as it
#: can *without* deliberating, not answer badly. A prompt that induced sloppiness would
#: manufacture the accuracy gap the study is supposed to measure.
DIRECT_SYSTEM = (
    "Answer the question directly with your final answer only. "
    "Do not show your work, do not reason step by step, and do not explain. "
    "Give the best answer you can in a single short response, "
    "with the final answer on its own last line."
)

#: Arm 2 imposes nothing on the reasoning. Steering how the model thinks would make the
#: trace an artifact of our prompt rather than of the model, and the trace is the object
#: of study.
THINKING_SYSTEM = (
    "Solve the problem. Think it through as carefully as you need to, "
    "then give the final answer on its own last line."
)


#: Arm 3 imposes nothing on the reasoning either, and adds one thing the other two do not
#: need: **the termination condition, stated**. "Answer without calling a tool" is what
#: ends the loop, and a model that does not know that spends turns confirming itself
#: against a `max_turns` of 6. It still does not say HOW to think -- see `react.py`.
REACT_SYSTEM = (
    "Solve the problem. You have tools available; use them when they help, and do not "
    "use them when they do not. When you have the answer, reply without calling any "
    "tool and give the final answer on its own last line."
)


#: Arm 1's effort. **Not "off" -- "off" is not purchasable on this model.** S7 found that
#: `reasoning_effort: "none"` and ollama's native `think: false` are both SILENTLY IGNORED
#: by gpt-oss:20b: they return a full 2918-character trace while appearing to be honoured.
#: `low` is honoured (131 chars, ~95% less). See ADR-004.
DIRECT_EFFORT = "low"


@dataclass(frozen=True)
class ArmSpec:
    """One arm's regime. Deliberately data, not code: the difference between the arms
    must be inspectable in one place rather than spread across two call sites."""

    strategy: Strategy
    system_prompt: str
    thinking: bool
    #: The effort to REQUEST. None means "use the pin's effort" (arm 2). Arm 1 names
    #: `low` explicitly rather than omitting the parameter -- omitting it gets the
    #: runtime's DEFAULT, which is close to arm 2's, and the two arms then barely differ.
    reasoning_effort: str | None
    #: C4.1: temperature 0 for Direct; the thinking arm uses provider defaults, because
    #: thinking is not meaningfully deterministic. **Recorded, not hidden** -- the report
    #: carries this flag so a reader knows which arms are reproducible run-to-run.
    deterministic: bool


ARMS: dict[str, ArmSpec] = {
    "direct": ArmSpec(
        "direct", DIRECT_SYSTEM, thinking=False, reasoning_effort=DIRECT_EFFORT, deterministic=True
    ),
    "thinking": ArmSpec(
        "thinking", THINKING_SYSTEM, thinking=True, reasoning_effort=None, deterministic=False
    ),
    # Arm 3 is a LOOP, not a single call, so `run_arm` dispatches it to `react.run_react`
    # rather than calling `generate` once. It is declared here anyway so that `--all-arms`,
    # `sorted(ARMS)` and the CLI's `--arm` choices all derive from one place -- an arm that
    # existed only inside a dispatch branch would be an arm the CLI could not name.
    "react": ArmSpec(
        "react", REACT_SYSTEM, thinking=True, reasoning_effort=None, deterministic=False
    ),
}


def messages_for(spec: ArmSpec, prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": spec.system_prompt},
        {"role": "user", "content": prompt},
    ]
