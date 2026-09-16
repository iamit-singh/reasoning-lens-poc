#!/usr/bin/env python3
"""Consistency false-positive rate on the known-good pool — M2-8's DoD, B4 #5.

    make consistency-fp          # runs the checker over pool.json's traces. COSTS SPEND.
    make consistency-fp ARGS="--dry-run"   # what it would ask, and what it would cost

**A false positive here is a `contradicts` verdict on a trace with no known defect.** The
pool is chosen by §4.4 before any judge has seen it (`scripts/select_pool.py`), which is
what makes this a measurement rather than a target.

The n problem, stated before the number rather than after it
------------------------------------------------------------
B4 #5's target is **FP ≤ 5%** and the known-good pool is **5 traces**. Those two numbers
are not compatible: the smallest non-zero false-positive rate observable at n = 5 is
**1/5 = 20%**. There is no outcome between 0% and 20%, so the target can only ever be read
as *"zero false flags"* — a 5% bar and a 0% bar are the same bar on this denominator.

That is not a reason to move the bar or the denominator. It is a reason to publish the
**count with its n and its interval** rather than a percentage: `0 of 5` says what was
measured; `0%` implies a resolution this sample does not have, and `20%` would read as a
catastrophe when it means *one trace out of five*. §5.3's own rule — every published number
carries its n and a CI — is doing real work here.

The tuning order, applied as C4.5 specifies
-------------------------------------------
If FP is non-zero: confirm `underdetermined` is not leaking into the flag count (it cannot;
`interpret` flags only on `contradicts`), then confirm the citation-required downgrade is
firing, and only then consider a prompt change — each of which bumps the bundle and
therefore voids the freeze. The downgrade is already applied from the start and **counted**,
so `downgrades` below is the evidence for step two rather than an assertion about it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))

from rlens import consistency as C
from rlens.contracts import NormalizedTrace, Step
from rlens.metrics import proportion

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"
POOL = ROOT / "calibration/seeded/pool.json"
OUT = ROOT / "calibration/results/consistency-fp.json"


def _trace_from(report: dict, arm: dict) -> NormalizedTrace:
    steps = [
        Step(
            step_id=s["step_id"],
            ordinal=i,
            kind=s.get("kind") or "thought",
            text=s.get("text") or "",
            span_id=s["step_id"].split(":")[1] if ":" in s["step_id"] else "x",
        )
        for i, s in enumerate(arm.get("steps") or [])
    ]
    return NormalizedTrace(
        strategy=arm["strategy"],
        item_id=report["item"]["id"],
        steps=steps,
        final_answer=arm.get("final_answer") or "",
        trace_quality=arm.get("trace_quality") or "full",
        model_pin=str(report.get("versions", {}).get("model_pin", "unknown")),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="list the traces; call nothing")
    args = ap.parse_args()

    if not POOL.is_file():
        print(
            f"no pool at {POOL.relative_to(ROOT)} -- run `make select-pool` first", file=sys.stderr
        )
        return 2
    pool = json.loads(POOL.read_text())
    wanted = set(pool["selected"])

    found: list[tuple[str, dict, dict]] = []
    for path in sorted(REPORTS.glob("*.report.json")):
        report = json.loads(path.read_text())
        for arm in report["arms"]:
            tid = f"{report['item']['id']}:{arm['strategy']}"
            if tid in wanted:
                found.append((tid, report, arm))

    missing = wanted - {t for t, _, _ in found}
    if missing:
        print(f"pool traces absent from the corpus: {sorted(missing)}", file=sys.stderr)
        return 2

    if args.dry_run:
        for tid, _r, arm in found:
            print(f"  {tid:<22} {len(arm.get('steps') or [])} steps")
        print(f"\n{len(found)} consistency calls would be made.")
        return 0

    results = []
    flagged = downgrades = skipped = 0
    for tid, report, arm in found:
        trace = _trace_from(report, arm)
        item_prompt = report["item"].get("prompt", "")
        out = C.check(trace, item_prompt=item_prompt)
        if out is None:
            skipped += 1
            results.append({"trace_id": tid, "verdict": None, "note": "not checked"})
            continue
        d = out.as_dict()
        if out.flagged:
            flagged += 1
        # `downgraded` is on the dataclass and deliberately NOT in `as_dict` -- the report
        # carries the verdict a reader sees, not the bookkeeping behind it. Read it here.
        downgrades += int(out.downgraded)
        results.append({"trace_id": tid, **d, "downgraded": out.downgraded})

    n = len(found) - skipped
    est = proportion(flagged, n, note=f"{flagged} of {n} known-good traces") if n else None
    doc = {
        "_README": (
            "M2-8 / B4 #5. A false positive is a `contradicts` verdict on a trace the "
            "pool selection deemed known-good. PUBLISHED AS A COUNT WITH ITS n: at n=5 the "
            "smallest non-zero rate is 20%, so a 5% target and a 0% target are the same "
            "target on this denominator, and a percentage would imply a resolution this "
            "sample does not have."
        ),
        "false_flags": flagged,
        "n_traces": n,
        "n_not_checked": skipped,
        "rate": round(flagged / n, 4) if n else None,
        "estimate": est.as_dict() if est is not None else None,
        "citation_downgrades_applied": downgrades,
        "target": "<= 0.05 (B4 #5) -- unresolvable below 20% at this n; read as 'zero'",
        "meets_target_read_as_zero": flagged == 0,
        "traces": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n")

    print("\nconsistency false flags · known-good pool")
    print("=" * 78)
    print(f"  false flags        {flagged} of {n}")
    print(f"  citation downgrades applied  {downgrades}")
    if skipped:
        print(f"  not checked        {skipped} (one-step trace, or the call failed)")
    print(
        f"  B4 #5              {'MET (zero)' if flagged == 0 else 'NOT MET'} "
        f"-- at n={n} the smallest non-zero rate is {1 / n:.0%}"
    )
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
