#!/usr/bin/env python3
"""Measure the escalation rate over the committed corpus — M2-5's DoD. Spends nothing.

    make escalation-rate

**It calls `judge.should_escalate` and `judge.select` rather than restating the policy.**
The first version of this reimplemented C4.4's three conditions inline, which is how a
measurement script silently goes on reporting the *old* policy after the policy changes —
and it did exactly that for one run before being caught. The policy has one definition and
this reads it.

Two rates, and both are published
---------------------------------
- **selected** — what the policy picks. This is the number trigger **t7** reads (> 25%).
- **escalated** — what survives `ESCALATION_MAX_STEPS`, so what is actually spent and what
  lands in the C11 latency budget.

Publishing only the second would hide that the policy selects far more than it escalates;
publishing only the first would claim a budget breach the cap is in fact preventing. C4.4's
own DoD asks for the rate, and a single number cannot answer both questions.

Degraded arms are excluded from the denominator, not counted as non-escalating
------------------------------------------------------------------------------
A chunk that fails to parse leaves its steps in the report with a null verdict. Those steps
have no policy input at all, so counting them as "did not escalate" would deflate the rate
by however much the classifier happened to fail that day.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))

from rlens.contracts import Step, StepRow
from rlens.judge import (
    LOW_CONFIDENCE,
    NUMERIC_CONFIDENCE,
    is_numeric,
    select,
    should_escalate,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"


def should_escalate_c4_4(row: StepRow, step: Step) -> bool:
    """C4.4's **original** first clause, kept only so the change can be measured.

    This is the one place a restatement of the policy is legitimate: it restates the policy
    that no longer exists, so that ADR-012 can publish a before and an after **over the same
    corpus snapshot**. Comparing a number taken last week against one taken today is not a
    before-and-after on this corpus -- the classifier is non-deterministic and the reports
    move under you, which is how the first attempt at this comparison went wrong.
    """
    if row.verdict != "sound":
        return True
    if row.validity_confidence < LOW_CONFIDENCE:
        return True
    return is_numeric(step.text) and row.validity_confidence < NUMERIC_CONFIDENCE


def _rows_and_steps(arm: dict) -> tuple[list[StepRow], dict[str, Step]]:
    rows: list[StepRow] = []
    steps: dict[str, Step] = {}
    for i, s in enumerate(arm.get("steps") or []):
        b = s.get("behavior") or {}
        v = s.get("validity") or {}
        if not b.get("label") or not v.get("verdict") or v.get("confidence") is None:
            continue  # degraded: no policy input
        rows.append(
            StepRow(
                step_id=s["step_id"],
                behavior=b["label"],
                behavior_confidence=b.get("confidence") or 0.0,
                verdict=v["verdict"],
                validity_confidence=v["confidence"],
                error_type=v.get("error_type"),
            )
        )
        steps[s["step_id"]] = Step(
            step_id=s["step_id"],
            ordinal=i,
            kind=s.get("kind") or "thought",
            text=s.get("text") or "",
            span_id=s["step_id"].split(":")[1] if ":" in s["step_id"] else "x",
        )
    return rows, steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    total = selected = escalated = 0
    old_selected = 0
    arms = capped_arms = 0
    by_verdict: collections.Counter[str] = collections.Counter()
    old_by_verdict: collections.Counter[str] = collections.Counter()
    worst: list[tuple[str, int, int, int]] = []

    for path in sorted(REPORTS.glob("*.report.json")):
        report = json.loads(path.read_text())
        for arm in report["arms"]:
            rows, steps = _rows_and_steps(arm)
            if not rows:
                continue
            arms += 1
            total += len(rows)
            chosen, capped, _rate = select(rows, steps)
            picked = [
                r for r in rows if r.step_id in steps and should_escalate(r, steps[r.step_id])
            ]
            old_picked = [
                r for r in rows if r.step_id in steps and should_escalate_c4_4(r, steps[r.step_id])
            ]
            selected += len(picked)
            old_selected += len(old_picked)
            for r in old_picked:
                old_by_verdict[r.verdict] += 1
            escalated += len(chosen)
            for r in picked:
                by_verdict[r.verdict] += 1
            if capped:
                capped_arms += 1
            worst.append(
                (f"{report['item']['id']}:{arm['strategy']}", len(picked), len(chosen), len(rows))
            )

    out = {
        "steps_with_a_usable_verdict": total,
        "selected": selected,
        "selected_rate": round(selected / total, 4) if total else None,
        "escalated_after_cap": escalated,
        "escalated_rate": round(escalated / total, 4) if total else None,
        "arms": arms,
        "arms_where_the_cap_bound": capped_arms,
        "selected_by_verdict": dict(by_verdict),
        "t7_fires": bool(total and selected / total > 0.25),
        "c4_4_original_selected": old_selected,
        "c4_4_original_rate": round(old_selected / total, 4) if total else None,
        "c4_4_original_by_verdict": dict(old_by_verdict),
        "c4_4_original_t7_fires": bool(total and old_selected / total > 0.25),
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"\nescalation rate · {arms} arms · {total} steps with a usable verdict")
    print("=" * 78)
    print(
        f"  selected by the policy    {selected:>4}  "
        f"({out['selected_rate']:.1%})   <- t7 reads this"
    )
    print(
        f"  escalated after the cap   {escalated:>4}  "
        f"({out['escalated_rate']:.1%})   <- what is spent"
    )
    print(f"  cap bound on              {capped_arms} arm(s)")
    print(f"  selected by verdict       {dict(by_verdict)}")
    print(f"  t7 (> 25% selected)       {'FIRES' if out['t7_fires'] else 'does not fire'}")
    print("\n  C4.4 as originally written (`verdict != sound`), SAME snapshot:")
    print(
        f"    selected                {old_selected:>4}  ({out['c4_4_original_rate']:.1%})  "
        f"t7 {'FIRES' if out['c4_4_original_t7_fires'] else 'does not fire'}"
    )
    print(f"    selected by verdict     {dict(old_by_verdict)}")
    print("\n  heaviest arms:")
    for trace, pick, esc, n in sorted(worst, key=lambda x: -x[1])[:6]:
        print(f"    {trace:<24} selected {pick:>3}/{n:<4} escalated {esc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
