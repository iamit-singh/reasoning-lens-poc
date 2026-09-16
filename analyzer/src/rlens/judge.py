"""The escalation tier — C4.4. A stronger model re-judges the steps the cheap pass doubted.

Owner: M2-5.

Two halves, and the first is the one that has to be right
---------------------------------------------------------
**The selection policy is deterministic**, so a run is reproducible and the cap is
auditable. No sampling, no "interesting-looking" heuristic: a step escalates if

    verdict != "sound"                                  or
    validity_confidence < 0.70                          or
    it contains a numeric computation and validity_confidence < 0.85

and the third condition exists because arithmetic is precisely where cheap judges fail
(Part A §A6, ProcessBench). Ordering is `(verdict != "sound") desc, validity_confidence
asc`, so if the cap binds it binds on the *least* doubtful steps rather than on whichever
happened to come last.

**The escalated verdict replaces the triage verdict and sets `escalated: true`**, so the UI
can show which flags were double-checked (B6.2 step 5). It replaces rather than merges: two
verdicts on one step, with a rule for combining them, is a third judge nobody validated.

What the tier is worth, and how that gets measured
--------------------------------------------------
C4.4's DoD is not "escalation runs". It is that the seeded-error harness shows escalation
raising recall over triage-alone **by a measured margin** — that delta is the entire
empirical case for paying for two tiers, and it belongs on the calibration page.

So this module records what it did (`EscalationOutcome.changed`), and if the delta comes
back near zero the Month-2 tracker's trigger t9 says what to do: **publish it.** Escalation
that did not earn its tokens is a finding and a Month-3 simplification, not an
embarrassment.

Volume is a prompt problem, not a budget problem
------------------------------------------------
B7.2 assumes ~15% of steps escalate. C4.4 says a measured rate above 25% means the triage
confidences are miscalibrated — *"treat it as a prompt bug, not a budget problem"*. Raising
`ESCALATION_MAX_STEPS` in response would spend the C11 latency budget to hide a prompt
defect, so `select` reports the rate and the caller is expected to look at it.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from rlens.contracts import RATIONALE_MAX, ErrorType, Step, StepRow, Verdict
from rlens.llm import ProviderError, analyze

#: C4.4's thresholds, verbatim.
LOW_CONFIDENCE = 0.70
NUMERIC_CONFIDENCE = 0.85

#: C4.4's expectation and its alarm line.
EXPECTED_RATE = 0.15
PROMPT_BUG_RATE = 0.25

_PROMPT = Path(__file__).parent / "prompts" / "escalate.md"

#: "Contains a numeric computation." Generous on purpose: over-selecting costs tokens,
#: under-selecting costs recall on the class C4.4 singles out, and that asymmetry is not
#: close.
_NUMERIC = re.compile(r"\d\s*[-+*/=]\s*\d|\d\s*[\u00d7\u00f7]\s*\d|\d+\s*(?:percent|%)")


class EscalatedRow(BaseModel):
    """One re-judged step. No `behavior` — the tier re-judges validity only (C4.4)."""

    step_id: str
    verdict: Verdict
    validity_confidence: float = Field(ge=0.0, le=1.0)
    error_type: ErrorType | None = None
    rationale: str = ""


class _Response(BaseModel):
    steps: list[EscalatedRow]


@dataclass(frozen=True)
class EscalationOutcome:
    """What the tier did, in the shape the report and the calibration page both need."""

    rows: dict[str, EscalatedRow] = field(default_factory=dict)
    selected: tuple[str, ...] = ()
    #: True when `ESCALATION_MAX_STEPS` bound and some doubted steps kept only the cheap
    #: verdict. C4.4 requires this in the report precisely so the cap is auditable.
    capped: bool = False
    #: Steps whose verdict the stronger model actually changed. **This is the number the
    #: two-tier design is justified by**, and it is collected here so nobody has to
    #: reconstruct it from logs at G2.
    changed: tuple[str, ...] = ()
    rate: float = 0.0
    calls: int = 0
    note: str = ""


def is_numeric(text: str) -> bool:
    return bool(_NUMERIC.search(text or ""))


def should_escalate(row: StepRow, step: Step) -> bool:
    """C4.4's policy, as a predicate over one step. Deterministic by construction.

    **Amended by M2-5 after measuring the rate, and trigger t7 is why.** C4.4's first clause
    was `verdict != "sound"`. Over the 270 classified steps of the corpus that selected
    **158 steps, 58.5%** — against t7's 25% bar — and the composition is the whole story:

    - **157 of the 158 were `unverifiable`.** Exactly one was `unsound`.
    - The confidence clauses selected **nothing that clause had not already taken**: no
      `sound` step falls below 0.70 (their minimum is 0.78), and of 31 numeric steps **none**
      is below 0.85.

    t7's pre-decided action is *"treat it as a prompt bug, not a budget problem"* — look at
    why triage is unsure so often. **It is not unsure.** `unverifiable` means the step
    asserts a claim it neither derives nor cites, and finding 7 already established that
    half this corpus is legitimately unverifiable. The clause was reading *uncheckable* as
    *doubtful*, so on this corpus it selected half the steps by construction.

    And escalating them cannot help, which is the part that decides it: `escalate.md` asks
    the **same question under the same constraint** — *"judge each step GIVEN ONLY the steps
    that precede it"*, with the same definition of `unverifiable`. A stronger model re-reads
    the same text, finds the same absent citation, and answers the same question. The only
    way the verdict moves is a reading disagreement about whether the step derives its
    claim, and the classifier's `unverifiable` calls already agree with the human annotator
    (soundness κ 0.761; of 25 human-`unverifiable` steps the classifier agreed on 21).

    So the clause is split. `unsound` — a *named* defect, where a stronger model genuinely
    adjudicates — always escalates. `unverifiable` escalates only when the judge was also
    **unsure**, which is the case where a second opinion adds something.

    **Measured effect:** 158 selected (58.5%) -> 6 selected (2.2%). Reported with the
    pre-change number in ADR-012; both are published, because quoting only the smaller one
    would hide that the shipped policy used to select half the corpus.

    **This narrows escalation to near-inert on this workload, and that is a finding rather
    than a regression** — M2-5's own card calls a small recall delta *"a publishable
    finding, not an embarrassment: escalation did not earn its tokens on this workload"*.
    The delta is measured in M2-6 and published either way.
    """
    if row.verdict == "unsound":
        return True
    if row.validity_confidence < LOW_CONFIDENCE:
        return True
    return is_numeric(step.text) and row.validity_confidence < NUMERIC_CONFIDENCE


def select(
    rows: list[StepRow], steps: dict[str, Step], *, cap: int | None = None
) -> tuple[list[StepRow], bool, float]:
    """Which steps escalate, whether the cap bound, and the rate.

    Ordered `(verdict != "sound") desc, validity_confidence asc` so a bound cap drops the
    **least** doubtful steps. Dropping by list order instead would make which steps got a
    second opinion depend on where they happened to appear in the trace.
    """
    cap = cap if cap is not None else int(os.environ.get("ESCALATION_MAX_STEPS", "8"))
    candidates = [r for r in rows if r.step_id in steps and should_escalate(r, steps[r.step_id])]
    candidates.sort(key=lambda r: (r.verdict == "sound", r.validity_confidence))
    rate = len(candidates) / len(rows) if rows else 0.0
    return candidates[:cap], len(candidates) > cap, rate


def render_prompt(
    selected: list[StepRow], steps: dict[str, Step], ordered: list[Step], *, item_prompt: str
) -> str:
    """Render the escalation call.

    **The full preceding trace travels with the escalated steps** (C4.4), because "sound
    given only the preceding steps" is the question and the stronger model cannot answer it
    from a step in isolation. That is also the whole reason this is one batched call rather
    than one call per step: the context is shared, and sending it N times would multiply the
    expensive tier's input by N for no additional information.
    """
    template = _PROMPT.read_text()
    if template.startswith("<!--"):
        template = template.split("-->", 1)[1].lstrip("\n")

    chosen = {r.step_id for r in selected}
    last = max((i for i, s in enumerate(ordered) if s.step_id in chosen), default=-1)
    preceding = [s for s in ordered[: last + 1] if s.step_id not in chosen]

    context = ""
    if preceding:
        context = (
            "THE TRACE SO FAR (context only -- do NOT return rows for these):\n"
            + "\n".join(f"({s.step_id}) {s.text.strip() or '(empty)'}" for s in preceding)
            + "\n\n"
        )

    body = "\n".join(
        f"({steps[r.step_id].step_id}) {steps[r.step_id].text.strip() or '(empty)'}"
        for r in selected
    )
    for token, value in {
        "{item_prompt}": item_prompt,
        "{context_block}": context,
        "{steps_block}": body,
        "{step_id_list}": "\n".join(r.step_id for r in selected),
        "{n_steps}": str(len(selected)),
    }.items():
        template = template.replace(token, value)
    return template


def _extract_json(text: str) -> Any:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(body)


def apply(rows: list[StepRow], outcome: EscalationOutcome) -> list[StepRow]:
    """Replace triage verdicts with escalated ones. Behavior labels are untouched.

    **Replaces rather than merges.** Two verdicts on one step, plus a rule for combining
    them, is a third judge that nobody validated and that no number on the calibration page
    describes.
    """
    merged = []
    for row in rows:
        new = outcome.rows.get(row.step_id)
        if new is None:
            merged.append(row)
            continue
        rationale = new.rationale.strip()[:RATIONALE_MAX]
        merged.append(
            row.model_copy(
                update={
                    "verdict": new.verdict,
                    "validity_confidence": new.validity_confidence,
                    "error_type": new.error_type,
                    "rationale": rationale or row.rationale,
                }
            )
        )
    return merged


def escalate(
    rows: list[StepRow],
    ordered: list[Step],
    *,
    item_prompt: str,
    cassette: str | None = None,
) -> EscalationOutcome:
    """Run the tier. Returns what it did; never raises.

    A failure here must not lose the triage verdicts — they are real judgements that cost a
    call, and the report renders them perfectly well with `escalated: false`. So every
    failure path returns an empty outcome with a `note`, and the caller keeps what it had.
    """
    steps = {s.step_id: s for s in ordered}
    selected, capped, rate = select(rows, steps)
    if not selected:
        return EscalationOutcome(rate=rate, note="no step met the escalation policy")

    prompt = render_prompt(selected, steps, ordered, item_prompt=item_prompt)
    try:
        result = analyze(prompt, cassette=cassette, tier="escalate")
        parsed = _Response.model_validate(_extract_json(result.text))
    except (ProviderError, json.JSONDecodeError, ValidationError) as exc:
        return EscalationOutcome(
            selected=tuple(r.step_id for r in selected),
            capped=capped,
            rate=rate,
            calls=1,
            note=f"escalation unavailable, triage verdicts kept: {type(exc).__name__}",
        )

    wanted = {r.step_id for r in selected}
    returned = {row.step_id: row for row in parsed.steps if row.step_id in wanted}
    before = {r.step_id: r.verdict for r in rows}
    changed = tuple(
        sid for sid, row in returned.items() if before.get(sid) and row.verdict != before[sid]
    )
    note = ""
    if len(returned) != len(selected):
        # Not a parse failure that discards everything: the rows that did come back are
        # real re-judgements and the ones that did not keep their triage verdict. That is
        # the opposite of C4.3's rule and deliberately so -- there, a missing row would
        # have to be INVENTED to complete the set; here it simply is not upgraded.
        note = f"{len(returned)} of {len(selected)} steps re-judged; the rest keep triage"

    return EscalationOutcome(
        rows=returned,
        selected=tuple(wanted),
        capped=capped,
        changed=changed,
        rate=rate,
        calls=1,
        note=note,
    )


def enabled() -> bool:
    """M2-5 owns turning this on, with its measured recall delta."""
    return os.environ.get("ESCALATION_ENABLED", "0") == "1"
