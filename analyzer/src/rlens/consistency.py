"""Whole-trace consistency — C4.5. Does the answer follow from these steps?

Owner: M2-8.

One call per strategy over the whole trace, and it asks exactly one question: **given only
these numbered steps, does the final answer follow?** Not whether the answer is right. Not
whether the model believed its own reasoning. B1 draws the honesty boundary here and this
module is where it is enforced in code rather than in copy.

Two rules that look like details and are not
--------------------------------------------
**1. Flag only on `contradicts`.** `underdetermined` is recorded and never shown as a
warning. B4 #5 targets a false-positive rate at or below 5% on known-good traces, and sound
traces are *routinely* underdetermined by their own written steps — models skip algebra they
consider obvious. Flagging that class is the single most likely way to blow the FP target
and make the instrument look broken on stage (B10).

**2. A `contradicts` verdict with no citation is downgraded to `underdetermined`.** C4.5
names this as the tuning lever if FP exceeds 5%; it is applied from the start rather than
held in reserve, because an accusation with no evidence is precisely the shape a
hallucinating judge produces, and there is no version of this project where we would want
to ship one. The downgrade is **counted**, so if it fires often that is a prompt problem
with a number attached rather than a silent correction.

The word this component never uses
----------------------------------
**"Faithful" does not appear in this module, its output, or any UI copy driven by it** —
C4.5 is explicit. Consistency asks whether the written steps support the answer.
Faithfulness asks whether those steps are the reasoning that actually produced it. They are
different questions, the second is much harder, and conflating them would let this project
claim the harder one on the easier one's evidence.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from rlens.contracts import NormalizedTrace
from rlens.llm import ProviderError, analyze

Verdict = Literal["entails", "contradicts", "underdetermined"]

#: C4.5's cap. Display text, capped rather than rejected -- the same trade `classify.py`
#: makes, for the same reason.
RATIONALE_MAX = 240

_PROMPT = Path(__file__).parent / "prompts" / "consistency.md"


class _Response(BaseModel):
    verdict: Verdict
    cited_step_ids: list[str] = []
    rationale: str = ""


@dataclass(frozen=True)
class Consistency:
    """One arm's consistency result, in the shape C3.3's report carries."""

    verdict: Verdict
    flagged: bool
    cited_step_ids: tuple[str, ...]
    rationale: str
    #: True when a `contradicts` verdict was downgraded for citing nothing (or for citing
    #: ids that are not in this trace). Counted rather than hidden: a high rate here is a
    #: prompt problem, and a prompt problem with a number attached is fixable.
    downgraded: bool = False
    calls: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "flagged": self.flagged,
            "cited_step_ids": list(self.cited_step_ids),
            "rationale": self.rationale or None,
        }


def render_prompt(trace: NormalizedTrace, *, item_prompt: str) -> str:
    template = _PROMPT.read_text()
    if template.startswith("<!--"):
        template = template.split("-->", 1)[1].lstrip("\n")
    steps = "\n".join(
        f"[{i + 1}] ({step.step_id}) {step.text.strip() or '(empty)'}"
        for i, step in enumerate(trace.steps)
    )
    for token, value in {
        "{item_prompt}": item_prompt,
        "{steps_block}": steps,
        "{final_answer}": trace.final_answer or "(no answer was given)",
        "{n_steps}": str(len(trace.steps)),
    }.items():
        template = template.replace(token, value)
    return template


def _extract_json(text: str) -> Any:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(body)


def interpret(payload: Any, trace: NormalizedTrace) -> Consistency:
    """Turn a parsed response into a verdict, applying C4.5's two rules.

    Separated from the call so both rules are testable without a model, which matters more
    here than usual: the FP rate this protects is a published number (B4 #5).
    """
    parsed = _Response.model_validate(payload)
    known = {step.step_id for step in trace.steps}

    # Citations that name steps not in this trace are dropped. A judge inventing a step id
    # is not a judge whose citation we should render next to real ones -- and the UI links
    # these, so an unknown id would be a dead link beside an accusation.
    cited = tuple(sid for sid in parsed.cited_step_ids if sid in known)
    verdict: Verdict = parsed.verdict
    downgraded = False

    if verdict == "contradicts" and not cited:
        verdict = "underdetermined"
        downgraded = True

    rationale = parsed.rationale.strip()
    if len(rationale) > RATIONALE_MAX:
        rationale = rationale[: RATIONALE_MAX - 1] + "…"
    if downgraded:
        rationale = (
            f"[downgraded from `contradicts`: no step of this trace was cited] {rationale}"
        )[:RATIONALE_MAX]

    return Consistency(
        verdict=verdict,
        # **Only `contradicts` flags.** The whole of C4.5's FP argument is this line.
        flagged=verdict == "contradicts",
        cited_step_ids=cited,
        rationale=rationale,
        downgraded=downgraded,
    )


def check(
    trace: NormalizedTrace,
    *,
    item_prompt: str,
    cassette: str | None = None,
) -> Consistency | None:
    """One consistency call. Returns None when the check could not be made.

    **None rather than a verdict on failure**, and rather than `underdetermined`:
    `underdetermined` is a judgement that the steps do not settle the question, and
    reporting it when no judge ran would put a conclusion in the report that nothing
    reached. C3.3 already types `consistency` as nullable for exactly this.
    """
    if len(trace.steps) < 2:
        # A one-step trace has nothing to be consistent with. The Direct arm often has
        # exactly one step plus an answer, and calling a model to ask whether an answer
        # follows from itself would bill for a question with no content.
        return None

    prompt = render_prompt(trace, item_prompt=item_prompt)
    try:
        result = analyze(prompt, cassette=cassette)
        return interpret(_extract_json(result.text), trace)
    except (ProviderError, json.JSONDecodeError, ValidationError):
        # One call, no repair retry. C4.3's retry exists because a malformed batch of 25
        # rows is worth one more attempt; a single three-field object that came back
        # malformed is a prompt or a model problem, and spending a second call on it buys
        # a second chance at the same coin flip.
        return None


def enabled() -> bool:
    """M2-8 owns turning this on. Off until its FP rate is measured.

    C4.5's DoD is a *measured* false-positive rate on the known-good set, and shipping the
    check before that number exists would put an unvalidated warning in front of a reviewer
    — which is the failure B10 is about.
    """
    return os.environ.get("CONSISTENCY_ENABLED", "0") == "1"
