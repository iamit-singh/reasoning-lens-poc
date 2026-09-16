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
    ap.add_argument(
        "--adopt-seeded",
        action="store_true",
        help="record the pool M2-6 already mutated, validated against §4.4",
    )
    args = ap.parse_args()

    judged = sorted(SEEDED.glob("SE-*.json")) + sorted((SEEDED / "reports").glob("*.json"))
    # `--adopt-seeded` is exempt from the "already exists" guard, and safely so: it does
    # not CHOOSE anything. It reads the base traces out of the committed SE-*.json cases,
    # so re-running it can correct a reporting field but cannot produce a different pool.
    # The guard exists to stop re-SELECTION, and this path has nothing to select.
    if POOL.exists() and not args.force and not args.adopt_seeded:
        print(
            f"a pool already exists at {POOL.relative_to(ROOT)} -- §4.4 says never "
            "re-select. Use --force only if no judge has run."
        )
        return 1

    # **The guard used to be on `--force` alone, and that was the wrong place.** The first
    # write is the dangerous one here: M2-6 ran in W5, ahead of its slot, and chose its own
    # five known-good traces to mutate. A *fresh* selection at this point is not "choosing
    # the pool" -- it is choosing a DIFFERENT pool than the one the judge has already been
    # scored against, which is exactly the swap rule 5 forbids, arriving through the door
    # nobody was watching. (It happened: the fresh run picked 4 of 5 traces M2-6 never
    # touched.) With seeded cases on disk the only honest pool is the one they were built
    # from, so `--adopt-seeded` is required and plain selection is refused.
    if judged and not args.adopt_seeded:
        print(
            "REFUSING to select: judge output already exists under calibration/seeded/.\n"
            "§4.4 rule 5 -- the pool is selected BEFORE any judge has run over it and never\n"
            "re-selected, because swapping a trace out because it drew flags converts the\n"
            "false-flag rate from a measurement into a target. M2-6 has already mutated and\n"
            "scored five traces; the pool is those five.\n"
            "Use --adopt-seeded to record them, validated against §4.4 with any deviation\n"
            "stated.",
            file=sys.stderr,
        )
        return 2

    if args.adopt_seeded:
        bases = set()
        for path in sorted(SEEDED.glob("SE-*.json")):
            case = json.loads(path.read_text())
            stem = pathlib.Path(case["base_span_path"]).stem  # e.g. "mb-07.thinking"
            item, _, strategy = stem.partition(".")
            bases.add(f"{item}:{strategy}")
        # Score EVERY trace, not just the adopted ones: `_write_pool` reports how many
        # traces were eligible and how many fell in the preferred band, and passing it
        # unscored rows made both read 0 -- a deviation note claiming the band was empty
        # when it has one member in it. A wrong number in the sentence explaining a
        # deviation is worse than no sentence.
        all_scored = []
        for tr in _traces():
            ok, why = _eligible(tr)
            all_scored.append({**tr, "eligible": ok, "reason": why})
        by_id = {t["trace_id"]: t for t in all_scored}
        adopted, problems = [], []
        for tid in sorted(bases):
            t_ = by_id.get(tid)
            if t_ is None:
                problems.append(f"{tid}: no arm with steps in the corpus")
                continue
            ok, why = _eligible(t_)
            if not ok:
                problems.append(f"{tid}: {why}")
            adopted.append(t_)
        _write_pool(adopted, all_scored, adopted_from_seeded=True, problems=problems)
        return 0 if not problems else 1

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

    _write_pool(pool, scored, adopted_from_seeded=False, problems=[])
    return 0


def _write_pool(
    pool: list[dict],
    scored: list[dict],
    *,
    adopted_from_seeded: bool,
    problems: list[str],
) -> None:
    """Write `pool.json`. Shared by both paths so they cannot describe the pool differently."""
    band_lo, band_hi = PREFERRED_STEPS
    in_band = [t["trace_id"] for t in pool if band_lo <= t["n_steps"] <= band_hi]
    eligible_in_band = sum(
        1 for t in scored if t.get("eligible") and band_lo <= t["n_steps"] <= band_hi
    )
    deviations = []
    if len(in_band) < len(pool):
        deviations.append(
            f"RULE 2 NOT MET and it is not satisfiable on this corpus: only "
            f"{eligible_in_band} eligible trace(s) fall in the {band_lo}-{band_hi} step band "
            f"at all. The corpus is bimodal -- most traces are 2-6 steps, then 8, 18, 40 and "
            f"141. Recorded rather than worked around: re-selecting for length would have "
            f"nothing to select."
        )
    primaries = Counter(t["tags"][0] if t["tags"] else "untagged" for t in pool)
    top, top_n = (primaries.most_common(1) or [("", 0)])[0]
    if top_n > len(pool) / 2:
        deviations.append(
            f"RULE 3 PARTIAL: {top_n} of {len(pool)} traces share the primary tag "
            f"'{top}'. Their full tag sets still differ; the false-flag rate is a property "
            f"of a narrower slice of the corpus than rule 3 intends, and that is stated "
            f"rather than corrected by swapping traces the judge has already scored."
        )
    if problems:
        deviations.extend(problems)

    doc = {
        "_README": (
            "M2-10a / §4.4. The five known-good traces. `labeled_step_coverage` is the "
            "honest caveat: rule 1 is applied to SAMPLED steps, and M2-15 -- which would "
            "have labelled every step of these five -- was dropped by amendment 002, so "
            "M2-7 publishes a per-labeled-step false-flag rate with the conversion to "
            "per-trace stated rather than performed."
        ),
        "provenance": (
            "ADOPTED from the traces M2-6 had already mutated and scored. M2-6 ran in W5, "
            "ahead of its slot and ahead of this task, so the pool was chosen then -- by "
            "M2-6's own selection -- and §4.4 rule 5 makes that choice final. A fresh "
            "selection here would have picked a DIFFERENT five (it did, on the run that "
            "caught this: 4 of its 5 were traces M2-6 never touched), which is the swap "
            "rule 5 exists to forbid, arriving after the judge had already been scored."
            if adopted_from_seeded
            else "Selected fresh, before any judge had run over the corpus."
        ),
        "criterion": [
            "1. every human-labeled step is sound or unverifiable; a trace with no "
            "labeled step is NOT eligible",
            "2. prefer 8-15 steps",
            "3. spread across tags",
            "4. no trap items",
            "5. selected before any judge ran; never re-selected",
        ],
        "deviations": deviations or ["none"],
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
        "tag_coverage": dict(primaries),
        "n_eligible": sum(1 for t in scored if t.get("eligible")),
        "n_eligible_in_the_preferred_band": eligible_in_band,
        "n_traces_considered": len(scored),
    }
    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"pool: {len(pool)} traces ({doc['n_eligible']} eligible of {len(scored)} considered)")
    for t in pool:
        print(
            f"  {t['trace_id']:<22} {t['n_steps']:>3} steps  "
            f"{t['n_labeled']:>2} labeled  {','.join(t['tags'])}"
        )
    print(f"  tag coverage: {doc['tag_coverage']}")
    for d in deviations:
        if d != "none":
            print(f"  ! {d}")
    print(f"  -> {POOL.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
