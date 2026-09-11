#!/usr/bin/env python3
"""Is `validity_confidence` a signal or a decoration? — M2-4, ADR-002's evidence.

    make confidence-histogram          # reads out/reports, no model, no network

**C4.4's escalation policy is built entirely on this number.** A step escalates if
`verdict != "sound"`, or `validity_confidence < 0.70`, or it contains a numeric computation
and `validity_confidence < 0.85`. Two of those three conditions are thresholds on one
float, so if the classifier emits a narrow band — say 0.8 to 0.9 on everything — the policy
degenerates to "escalate the unsound ones", the frontier tier never sees a
low-confidence-but-sound step, and **the two-tier design stops being a design**.

That failure is invisible from the outside: escalation still runs, the report still carries
`escalated`, and the rate looks plausible. It shows up only as a histogram.

The Month-2 tracker carries it as a named trigger (t8): *validity_confidence degenerate →
the policy falls back to `verdict != sound` plus all numeric steps; re-check volume against
the cap and C11; record as a design change.* This script is what fires it.

What it measures, and one thing it measures that C4.4 did not anticipate
-----------------------------------------------------------------------
* the distribution and spread of both confidences,
* **how often the two are byte-identical** — a first sample showed 23% of rows with
  `behavior_confidence == validity_confidence`, which would mean the model is emitting one
  number twice rather than judging two different questions,
* and how many steps each escalation condition would actually select, which is the number
  C4.4's "~15% expected, treat >25% as a prompt bug" is about.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"

#: C4.4's thresholds, verbatim.
LOW = 0.70
NUMERIC_LOW = 0.85

#: "contains a numeric computation" -- two or more numbers and an operator, or an equals
#: sign between numbers. Deliberately generous: C4.4 says arithmetic is precisely where
#: cheap judges fail, so over-selecting here costs tokens while under-selecting costs
#: recall, and the asymmetry is not close.
_NUMERIC = re.compile(r"\d\s*[-+*/=]\s*\d|\d\s*[\u00d7\u00f7]\s*\d|\d+\s*(?:percent|%)")


def _buckets(values: list[float], width: float = 0.05) -> list[tuple[str, int]]:
    counts: collections.Counter[int] = collections.Counter()
    for v in values:
        counts[min(int(v / width), int(1 / width) - 1)] += 1
    return [
        (f"{i * width:.2f}-{(i + 1) * width:.2f}", counts.get(i, 0))
        for i in range(int(1 / width))
        if counts.get(i, 0)
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", default=str(REPORTS))
    args = ap.parse_args(argv)

    reports = pathlib.Path(args.reports)
    if not reports.is_dir() or not list(reports.glob("*.report.json")):
        print(
            f"no reports at {reports}. Run `make report ARGS=--all` first.",
            file=sys.stderr,
        )
        return 2

    behavior: list[float] = []
    validity: list[float] = []
    identical = 0
    rows = 0
    numeric_rows = 0
    esc_unsound = esc_low = esc_numeric = 0
    verdicts: collections.Counter[str] = collections.Counter()

    for path in sorted(reports.glob("*.report.json")):
        report = json.loads(path.read_text())
        for arm in report["arms"]:
            for step in arm["steps"]:
                b, v = step.get("behavior"), step.get("validity")
                if not b or not v:
                    continue
                rows += 1
                behavior.append(b["confidence"])
                validity.append(v["confidence"])
                if b["confidence"] == v["confidence"]:
                    identical += 1
                verdicts[v["verdict"]] += 1

                is_numeric = bool(_NUMERIC.search(step.get("text") or ""))
                numeric_rows += is_numeric
                unsound = v["verdict"] != "sound"
                low = v["confidence"] < LOW
                num_low = is_numeric and v["confidence"] < NUMERIC_LOW
                esc_unsound += unsound
                esc_low += low and not unsound
                esc_numeric += num_low and not unsound and not low

    if not rows:
        print("no classified steps in those reports.", file=sys.stderr)
        return 2

    print(f"M2-4 · confidence distribution over {rows} classified steps\n")
    for name, values in (("behavior_confidence", behavior), ("validity_confidence", validity)):
        spread = max(values) - min(values)
        print(
            f"  {name:22s} min {min(values):.2f}  median {statistics.median(values):.2f}  "
            f"max {max(values):.2f}  spread {spread:.2f}  distinct {len(set(values))}"
        )
    print()
    for name, values in (("behavior", behavior), ("validity", validity)):
        print(f"  {name} histogram")
        peak = max(c for _, c in _buckets(values)) or 1
        for label, count in _buckets(values):
            bar = "█" * max(1, round(40 * count / peak))
            print(f"    {label}  {count:4d}  {bar}")
        print()

    share = 100 * identical / rows
    print(f"  identical confidences   {identical} of {rows} rows ({share:.1f}%)")
    if share > 50:
        print(
            "    ⚠ The model is emitting ONE number twice rather than judging two questions.\n"
            "      Both halves of the merged call (C4.3) are supposed to be separately\n"
            "      judged; a shared confidence means one of them is decoration."
        )

    print(f"\n  verdicts                {dict(verdicts)}")
    total_esc = esc_unsound + esc_low + esc_numeric
    print("\n  C4.4 escalation policy, applied to these rows")
    print(f"    verdict != sound          {esc_unsound:4d}")
    print(f"    + validity_conf < {LOW}     {esc_low:4d}")
    print(
        f"    + numeric & < {NUMERIC_LOW}       {esc_numeric:4d}"
        f"   (of {numeric_rows} numeric steps)"
    )
    print(f"    = escalated               {total_esc:4d}  ({100 * total_esc / rows:.1f}% of steps)")

    # C4.4: ~15% expected; >25% is a prompt bug, not a budget problem.
    rate = 100 * total_esc / rows
    if rate > 25:
        print("\n  ⚠ Above C4.4's 25% line. Treat as a PROMPT bug, not a budget problem —")
        print("    raising ESCALATION_MAX_STEPS breaks the C11 latency budget instead.")
    if esc_low + esc_numeric == 0:
        print(
            "\n  ⚠ TRIGGER t8: the confidence thresholds select NOTHING. Every escalation\n"
            "    here comes from `verdict != sound`, so the two-tier design reduces to\n"
            "    're-judge the flagged ones' and the confidence half is inert. C4.4's\n"
            "    fallback is verdict != sound plus ALL numeric steps — record it as a\n"
            "    design change in ADR-002 rather than leaving the policy looking intact."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
