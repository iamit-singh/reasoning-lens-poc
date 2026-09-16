#!/usr/bin/env python3
"""Select the 5 known-good traces — M2-10a's second half, §4.4.

    make select-pool            # writes calibration/seeded/pool.json
    make select-pool ARGS="--force"   # re-select. Refuses once a judge has run.

**The whole point of this script is *when* it runs, not what it computes.** The five
traces are the denominator of the known-good false-flag rate (B4 #4) and the clean half of
M2-7's precision pool. Choosing them *after* the flags are known would let the pool be
chosen to flatter the rate — swap out the trace that drew three flags and the number
improves without the judge changing at all. §4.4's own sentence: *selected before the judge
has run over them, and never re-selected afterwards.*

So the refusal is the feature. `--force` exists because a genuine re-selection is possible
before any judge output exists (M2-15's card provides for re-selecting *for shorter traces*
before labelling starts), and it refuses outright once `calibration/seeded/` holds judge
results — at which point re-selection is the contamination rule 5 forbids.

The four rules, applied in order (§4.4)
---------------------------------------
1. **Human-labeled sound** — every *sampled* step in the trace labeled `sound`.
   `unverifiable` is acceptable; a single `unsound` disqualifies the trace.
2. **Modest step count** — prefer 8-15 steps.
3. **Tag coverage** — not all five from one tag, or the false-flag rate becomes a property
   of one problem type.
4. **No trap items** — a trap exists to induce a plausible wrong chain, so a trace on a
   trap item is not a known-good trace even when it happens to be right.

What "sampled" means here, and why it is the honest word
--------------------------------------------------------
Rule 1 can only be applied to steps a human actually labeled, and the calibration draw is
a 150-step sample scattered across 42 traces — typically 3-4 labeled steps in a 15-25 step
trace. A trace passing rule 1 therefore means *no labeled step is unsound*, *not* *no step
is unsound*. That gap is exactly what M2-15 existed to close by labelling every step of the
five, and **amendment 002 dropped M2-15** (it is human labelling, and §2 governs it).

The gap is therefore permanent, and it is recorded in `pool.json` itself rather than left
for a reader to infer: `labeled_step_coverage` carries, per trace, how many of its steps
carry a human label. M2-7 publishes a **per-labeled-step** false-flag rate with the
conversion to per-trace stated rather than performed — the §1.3.1 fallback, taken
consciously.

**A trace with zero labeled steps is not eligible.** Rule 1 is vacuously true for it, which
is precisely the reading that would let an unexamined trace into the set that defines
"known good".
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"
BANK = ROOT / "problem-bank/items"
LABELS = ROOT / "calibration/labels"
SEEDED = ROOT / "calibration/seeded"
POOL = SEEDED / "pool.json"

TARGET = 5
PREFERRED_STEPS = (8, 15)


def _labels() -> dict[str, str]:
    """step_id -> soundness label, over every committed human label file.

    Both halves are read. This is not a C5.4 violation: the held-out guard protects the
    held-out labels from being *scored against the classifier*, and nothing here scores
    anything — it reads which steps a human called unsound in order to keep them out of a
    set defined as known-good. Excluding the held-out labels would make a trace look clean
    because the one step a human flagged happened to fall in the other half of the draw.
    """
    out: dict[str, str] = {}
    for path in sorted(LABELS.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            # First writer wins, so a second annotator cannot silently overwrite the first.
            out.setdefault(row["step_id"], row["soundness_label"])
    return out


def _bank() -> dict[str, dict]:
    items = [json.loads(p.read_text()) for p in sorted(BANK.glob("*.json"))]
    return {item["id"]: item for item in items}


def _traces() -> list[dict]:
    """Every (item, arm) trace that produced steps, with what the rules need."""
    bank, labels, out = _bank(), _labels(), []
    for path in sorted(REPORTS.glob("*.report.json")):
        report = json.loads(path.read_text())
        item_id = report["item"]["id"]
        item = bank.get(item_id, {})
        for arm in report["arms"]:
            steps = arm.get("steps") or []
            if not steps:
                continue
            marks = [labels[s["step_id"]] for s in steps if s["step_id"] in labels]
            out.append(
                {
                    "trace_id": f"{item_id}:{arm['strategy']}",
                    "item_id": item_id,
                    "strategy": arm["strategy"],
                    "tags": list(item.get("tags") or []),
                    "is_trap": bool(item.get("is_trap")),
                    "n_steps": len(steps),
                    "n_labeled": len(marks),
                    "n_unsound": sum(1 for m in marks if m == "unsound"),
                    "status": arm.get("status"),
                }
            )
    return out


def _eligible(t: dict) -> tuple[bool, str]:
    if t["status"] != "ok":
        return False, f"arm status {t['status']!r}"
    if t["is_trap"]:
        return False, "rule 4: trap item"
    if t["n_labeled"] == 0:
        return False, "rule 1: no human-labeled step -- vacuously clean is not clean"
    if t["n_unsound"]:
        return False, f"rule 1: {t['n_unsound']} step(s) labeled unsound"
    return True, "eligible"


def _rank(t: dict) -> tuple:
    """Rule 2 as an ordering: inside the 8-15 band first, then closest to it.

    Deterministic all the way down -- the trace id is the final key -- so the selection
    reproduces from the same corpus without a seed.
    """
    lo, hi = PREFERRED_STEPS
    n = t["n_steps"]
    inside = 0 if lo <= n <= hi else 1
    distance = 0 if inside == 0 else (lo - n if n < lo else n - hi)
    return (inside, distance, -t["n_labeled"], t["trace_id"])


def select(traces: list[dict]) -> tuple[list[dict], list[dict]]:
    scored = []
    for t in traces:
        ok, why = _eligible(t)
        scored.append({**t, "eligible": ok, "reason": why})

    pool: list[dict] = []
    tags_used: Counter[str] = Counter()
    candidates = sorted([t for t in scored if t["eligible"]], key=_rank)

    # Rule 3 as a two-pass fill: take the best candidate whose primary tag is unused, and
    # only then relax. Enforcing tag coverage by rejection would let rule 3 empty the pool
    # on a corpus with few tags; enforcing it by ORDER spends the coverage budget first and
    # still fills five.
    for t in candidates:
        if len(pool) >= TARGET:
            break
        primary = t["tags"][0] if t["tags"] else "untagged"
        if tags_used[primary] == 0:
            pool.append(t)
            tags_used[primary] += 1
    for t in candidates:
        if len(pool) >= TARGET:
            break
        if t not in pool:
            pool.append(t)
            tags_used[t["tags"][0] if t["tags"] else "untagged"] += 1

    return pool, scored


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--force", action="store_true", help="re-select; refuses once judge output exists"
    )
    args = ap.parse_args()

    judged = sorted(SEEDED.glob("SE-*.json")) + sorted((SEEDED / "reports").glob("*.json"))
    if POOL.exists() and not args.force:
        print(
            f"a pool already exists at {POOL.relative_to(ROOT)} -- §4.4 says never "
            "re-select. Use --force only if no judge has run."
        )
        return 1
    if POOL.exists() and args.force and judged:
        print(
            "REFUSING to re-select: judge output already exists under calibration/seeded/.\n"
            "§4.4 rule 5 -- swapping a trace out of the pool because it drew flags converts\n"
            "the false-flag rate from a measurement into a target.",
            file=sys.stderr,
        )
        return 2

    traces = _traces()
    if not traces:
        print(
            f"no reports under {REPORTS.relative_to(ROOT)} -- run the corpus first (M2-10a)",
            file=sys.stderr,
        )
        return 2

    pool, scored = select(traces)
    if len(pool) < TARGET:
        print(
            f"only {len(pool)} of {TARGET} traces are eligible -- see the rejections below",
            file=sys.stderr,
        )

    doc = {
        "_README": (
            "M2-10a / §4.4. The five known-good traces, chosen BEFORE any judge ran over "
            "them and never re-selected. `labeled_step_coverage` is the honest caveat: rule "
            "1 is applied to SAMPLED steps, and M2-15 -- which would have labelled every "
            "step of these five -- was dropped by amendment 002. M2-7 therefore publishes a "
            "per-labeled-step false-flag rate with the conversion to per-trace stated."
        ),
        "criterion": [
            "1. every human-labeled step is sound or unverifiable; a trace with no "
            "labeled step is NOT eligible",
            "2. prefer 8-15 steps",
            "3. spread across tags -- coverage spent first, by ordering, not by rejection",
            "4. no trap items",
            "5. selected before any judge ran; never re-selected",
        ],
        "selected": [t["trace_id"] for t in pool],
        "traces": [
            {
                "trace_id": t["trace_id"],
                "item_id": t["item_id"],
                "strategy": t["strategy"],
                "tags": t["tags"],
                "n_steps": t["n_steps"],
                "labeled_step_coverage": f"{t['n_labeled']}/{t['n_steps']}",
            }
            for t in pool
        ],
        "tag_coverage": dict(Counter(t["tags"][0] if t["tags"] else "untagged" for t in pool)),
        "rejected": [
            {"trace_id": t["trace_id"], "reason": t["reason"], "n_steps": t["n_steps"]}
            for t in scored
            if not t["eligible"]
        ],
        "n_eligible": sum(1 for t in scored if t["eligible"]),
        "n_traces_considered": len(scored),
    }
    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"selected {len(pool)} of {doc['n_eligible']} eligible ({len(scored)} traces considered)")
    for t in pool:
        print(
            f"  {t['trace_id']:<22} {t['n_steps']:>3} steps  "
            f"{t['n_labeled']:>2} labeled  {','.join(t['tags'])}"
        )
    print(f"  tag coverage: {doc['tag_coverage']}")
    print(f"  -> {POOL.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
