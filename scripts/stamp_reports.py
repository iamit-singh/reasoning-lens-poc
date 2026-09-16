#!/usr/bin/env python3
"""Stamp `measurement_context` and the verdict lines into every report — M2-10b.

    make stamp-reports              # after M2-17 has written results/latest.json
    make stamp-reports ARGS="--check"   # verify without writing (CI, G2 evidence)

**Hazard 3: this runs after M2-17, never before.** `measurement_context` is the block that
makes a soundness score readable — it carries the κ, the precision and the recall that say
how much to trust the number beside them. Stamping it from a `latest.json` written before
the final run would put dev numbers on 42 reports and label them as the measurement.

What it writes
--------------
1. **`measurement_context`** on every report, copied from `calibration/results/latest.json`.
   Copied, not recomputed: two code paths that both "compute the κ" eventually disagree,
   and the one in the report would be the one nobody re-checks.
2. **`scoreboard.verdict_line`**, selected by C4.6's four templates from **measured facts**.
   Never free-form prose, and never a template whose facts are missing.
3. **`metrics.est_cost_usd`**, if and only if `analyzer/prices.json` carries real rates.
   It ships null today and the price table says why.

The rule that makes the stamp worth having
-------------------------------------------
A report whose `measurement_context` is absent or stale must FAIL validation — I3's whole
point is that a soundness score cannot render without its error bars, and forbidding the
unsafe state in the schema is cheaper than catching it in a Month-3 UI review. `--check`
is that assertion, runnable on its own so the G2 evidence pack can show it green.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"
LATEST = ROOT / "calibration/results/latest.json"
PRICES = ROOT / "analyzer/prices.json"

# C4.6's four templates, VERBATIM. The multiplication sign is the plan's character and the
# one the UI renders; ruff flags it as ambiguous (RUF001) and the suppression is here, once,
# rather than spread over the call sites -- changing published copy to satisfy a linter is
# how a template stops being the template.
T_TOOL = "Only the tool-using agent could ground this — the others guessed fluently."
T_EARNED = "Thinking earned its tokens here: +{delta:.0f} pp accuracy for {ratio}× the output cost."  # noqa: RUF001
T_SPENT = "Extended thinking spent {ratio}× the output tokens of Direct for the same answer."  # noqa: RUF001
T_FLAGGED = "{flagged} step(s) flagged; {confirmed} confirmed by the escalated judge."


def _prices() -> dict:
    return json.loads(PRICES.read_text()) if PRICES.is_file() else {}


def _cost(metrics: dict, model: str, prices: dict) -> float | None:
    """Estimated dollars, or None when the rate is not priced.

    **None rather than 0.0.** A zero cost is a claim that the call was free, which is true
    for the local generation tier and false for every analysis call; rendering an unpriced
    model as $0.00 would understate the spend line by exactly the amount nobody checked.
    """
    entry = (prices.get("models") or {}).get(model) or {}
    if not entry.get("priced"):
        return None
    inp, out = entry.get("input"), entry.get("output")
    if inp is None or out is None:
        return None
    i = metrics.get("input_tokens") or 0
    o = metrics.get("output_tokens") or 0
    return round((i * inp + o * out) / 1_000_000, 6)


def verdict_line(report: dict) -> str | None:
    """C4.6's templates, selected by measured facts. Returns None when no template applies.

    **None is a real answer here.** The templates describe four situations; a trace in none
    of them has nothing interesting to say, and inventing a fifth sentence to fill the field
    is exactly the free-form prose C4.6 forbids. The UI renders the absence.
    """
    by = {a["strategy"]: a for a in report["arms"]}
    direct, thinking, react = by.get("direct"), by.get("thinking"), by.get("react")
    sb = report.get("scoreboard") or {}
    ratio = sb.get("cost_of_thought_ratio")
    tags = (report.get("item") or {}).get("tags") or []

    # 3. ReAct alone grounded a tool_required item. Checked first: it is the most specific
    #    claim and the one a reader learns most from.
    if "tool_required" in tags and react and react.get("correct"):
        others = [a for a in (direct, thinking) if a and a.get("correct") is not None]
        if others and not any(a["correct"] for a in others):
            return T_TOOL

    # 2. Thinking earned its tokens.
    if direct and thinking and thinking.get("correct") and direct.get("correct") is False:
        delta = sb.get("accuracy_delta_pp")
        if delta is not None and ratio:
            return T_EARNED.format(delta=delta, ratio=ratio)

    # 1. Same answer, and thinking spent at least 3x the tokens to reach it.
    if (
        direct
        and thinking
        and direct.get("correct") == thinking.get("correct")
        and ratio
        and ratio >= 3
    ):
        return T_SPENT.format(ratio=ratio)

    # 4. Anything was flagged. Last, because it is the least specific.
    flagged = sum((a.get("metrics") or {}).get("flagged_step_count") or 0 for a in report["arms"])
    if flagged:
        confirmed = sum(
            1
            for a in report["arms"]
            for s in (a.get("steps") or [])
            if (s.get("validity") or {}).get("escalated")
        )
        return T_FLAGGED.format(flagged=flagged, confirmed=confirmed)

    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify, write nothing")
    args = ap.parse_args()

    if not LATEST.is_file():
        print(f"no {LATEST.relative_to(ROOT)} -- M2-17 writes it", file=sys.stderr)
        return 2
    latest = json.loads(LATEST.read_text())
    ctx = latest.get("measurement_context")
    if not ctx:
        print("latest.json carries no measurement_context", file=sys.stderr)
        return 2

    run_id = ctx.get("calibration_run_id")
    prices = _prices()
    paths = sorted(REPORTS.glob("*.report.json"))
    if not paths:
        print(f"no reports under {REPORTS.relative_to(ROOT)}", file=sys.stderr)
        return 2

    stale, stamped, lines = [], 0, 0
    for path in paths:
        report = json.loads(path.read_text())
        current = report.get("measurement_context") or {}
        if args.check:
            if not current or current.get("calibration_run_id") != run_id:
                stale.append(path.name)
            continue

        report["measurement_context"] = dict(ctx)
        stamped += 1
        vl = verdict_line(report)
        report.setdefault("scoreboard", {})["verdict_line"] = vl
        if vl:
            lines += 1
        model = (report.get("versions") or {}).get("judge_triage_pin") or ""
        for arm in report["arms"]:
            m = arm.get("metrics") or {}
            m["est_cost_usd"] = _cost(m, model, prices)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if args.check:
        if stale:
            print(
                f"STALE: {len(stale)} of {len(paths)} reports do not carry "
                f"calibration_run_id {run_id!r}.\n"
                "A soundness score rendered without the measurement that qualifies it is "
                "the I3 failure this stamp exists to prevent.\n"
                f"  {', '.join(stale[:6])}{' ...' if len(stale) > 6 else ''}",
                file=sys.stderr,
            )
            return 1
        print(f"stamp-check: OK -- {len(paths)} reports carry calibration_run_id {run_id!r}")
        return 0

    priced = any((e or {}).get("priced") for e in (prices.get("models") or {}).values())
    print(f"stamped {stamped} reports from calibration_run_id {run_id!r}")
    print(f"  verdict lines written : {lines} of {stamped} (None is a real answer -- C4.6)")
    print(
        f"  est_cost_usd          : {'computed' if priced else 'null -- see analyzer/prices.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
