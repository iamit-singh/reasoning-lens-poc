#!/usr/bin/env python3
"""Pooled judge precision + the known-good false-flag rate — M2-7, B4 #4.

    make pooled-precision

Reads committed artefacts only: `out/reports/`, `calibration/seeded/`, the human labels and
`pool.json`. **It calls no model**, so it is free, deterministic and re-runnable.

C5.6's construction, and why B4 #4 needed one
----------------------------------------------
B4 #4 as originally written is unmeasurable: precision over a set where every step is sound
is 0 or undefined by construction. C5.6 resolves it (C0.3 #1) by pooling:

    Pool  = 5 known-good traces + 5 seeded-error traces (10 planted flaws)
    genuine flaw := a planted flaw at its expected step id
                    OR a step the human annotator labeled `unsound`
    precision    = flags on genuine flaws / all flags raised over the pool

**Including naturally-occurring `unsound` steps is not a nicety**: without it, a judge that
correctly catches a real error inside a known-good trace is scored as wrong.

The asymmetry this script refuses to ship quietly
--------------------------------------------------
A **flag** in this pipeline is `verdict not in (None, "sound")` — so it includes
`unverifiable`. ADR-012 already ruled that for **recall**, an `unverifiable` verdict on a
planted flaw **counts as a hit**: *"the seeded step is defective; a judge that stopped and
said 'I cannot verify this' did not miss it."*

Applying that rule to recall and *not* to precision would be a one-way ratchet — every
`unverifiable` call helps recall and hurts precision, on a corpus where **half the steps are
legitimately unverifiable** (finding 7). That is the shape of a number chosen to look good.

So **both are computed and both are published**:

- `precision_strict` — C5.6 read literally. A genuine flaw must be a planted flaw or a
  human `unsound`. Every `unverifiable` flag is a false positive, including the ones a human
  independently called `unverifiable`.
- `precision_symmetric` — the same rule ADR-012 applied to recall, applied here: a flag is
  on a genuine flaw when the human **agreed the step was not sound**, whichever of the two
  non-sound verdicts either of them used.

Neither is presented as *the* number. The strict one is the plan's literal definition and
the conservative floor; the symmetric one is the one whose treatment of `unverifiable`
matches the recall it will be printed next to. The G2 report quotes both with this
paragraph, because a reader who sees only one cannot tell which convention produced it.

The false-flag rate, and the denominator that no longer exists
--------------------------------------------------------------
B4 #4's second clause is *"≤ 1 false flag per known-good trace"*. That per-trace figure
needs every step of the five traces labelled by a human — **M2-15, which amendment 002
dropped**. So the per-trace rate is **not computed here**. What ships instead is the
§1.3.1 fallback: a **per-labelled-step** rate, with the conversion to per-trace stated
rather than performed, and `labelled_step_coverage` carried alongside so a reader can see
exactly how much of each trace was examined.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))

from rlens.metrics import proportion

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "out/reports"
LABELS = ROOT / "calibration/labels"
SEEDED = ROOT / "calibration/seeded"
POOL = SEEDED / "pool.json"
OUT = ROOT / "calibration/results/pooled-precision.json"

NOT_SOUND = ("unsound", "unverifiable")


def human_labels() -> dict[str, str]:
    """step_id -> soundness label. First writer wins, so annotator 2 cannot overwrite 1."""
    out: dict[str, str] = {}
    for path in sorted(LABELS.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                out.setdefault(row["step_id"], row["soundness_label"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    if not POOL.is_file():
        print(f"no pool at {POOL.relative_to(ROOT)} -- run `make select-pool`", file=sys.stderr)
        return 2

    pool = json.loads(POOL.read_text())
    known_good = set(pool["selected"])
    labels = human_labels()

    flags_strict = flags_sym = 0
    hits_strict = hits_sym = 0
    false_flags_on_labelled_sound = 0
    labelled_steps = 0
    per_trace: dict[str, dict] = {}

    # ---- the known-good half, from the committed corpus
    for path in sorted(REPORTS.glob("*.report.json")):
        report = json.loads(path.read_text())
        for arm in report["arms"]:
            tid = f"{report['item']['id']}:{arm['strategy']}"
            if tid not in known_good:
                continue
            steps = arm.get("steps") or []
            t = per_trace.setdefault(
                tid, {"steps": len(steps), "labelled": 0, "flags": 0, "false_flags": 0}
            )
            for s in steps:
                verdict = (s.get("validity") or {}).get("verdict")
                if verdict is None:
                    continue
                human = labels.get(s["step_id"])
                if human:
                    t["labelled"] += 1
                    labelled_steps += 1
                if verdict in NOT_SOUND:
                    t["flags"] += 1
                    flags_strict += 1
                    flags_sym += 1
                    # strict: a genuine flaw requires human `unsound`
                    if human == "unsound":
                        hits_strict += 1
                        hits_sym += 1
                    elif human in NOT_SOUND:
                        # symmetric: the human also said "not sound"
                        hits_sym += 1
                    elif human == "sound":
                        # A flag on a step a human read and called sound. This is the only
                        # unambiguous false positive in the whole construction.
                        t["false_flags"] += 1
                        false_flags_on_labelled_sound += 1

    # ---- the seeded half, from the committed mutation results
    seeded_hits = 0
    seeded_reports = sorted((SEEDED / "reports").glob("*.json"))
    for path in seeded_reports:
        blob = json.loads(path.read_text())
        flagged = blob.get("judge_flagged_steps") or []
        # The planted flaw's step id. `SE-*.json` carries an ORDINAL, not an id -- the id
        # is resolved when the mutation is applied, and the built report is where it is
        # recorded. Reading it from there is also what `build_replay_reports.py` does, so
        # the two cannot disagree about which step was broken.
        expected = blob.get("mutated_step_id")
        for sid in flagged:
            flags_strict += 1
            flags_sym += 1
            if expected and sid == expected:
                hits_strict += 1
                hits_sym += 1
                seeded_hits += 1
            elif labels.get(sid) == "unsound":
                hits_strict += 1
                hits_sym += 1
            elif labels.get(sid) in NOT_SOUND:
                hits_sym += 1

    doc = {
        "_README": (
            "M2-7 / B4 #4, C5.6's pooled construction. TWO precision figures are published "
            "and neither is 'the' number: `strict` reads C5.6 literally (a genuine flaw is "
            "a planted flaw or a human `unsound`), `symmetric` applies the rule ADR-012 "
            "already applied to RECALL -- that an `unverifiable` verdict on a defective "
            "step is not a miss -- to precision as well. Using ADR-012's rule for recall "
            "and not for precision would be a one-way ratchet on a corpus that is half "
            "legitimately unverifiable (finding 7). "
            "THE PER-TRACE FALSE-FLAG RATE IS NOT COMPUTED: it needs every step of the five "
            "traces human-labelled (M2-15), which amendment 002 dropped. The per-labelled-"
            "step rate below is SS1.3.1's stated fallback, second-best and taken knowingly."
        ),
        "precision_strict": proportion(hits_strict, flags_strict).as_dict()
        if flags_strict
        else None,
        "precision_symmetric": proportion(hits_sym, flags_sym).as_dict() if flags_sym else None,
        "flags_raised_over_the_pool": flags_strict,
        "seeded_reports_read": len(seeded_reports),
        "false_flags_on_human_labelled_sound_steps": false_flags_on_labelled_sound,
        "human_labelled_steps_in_the_known_good_pool": labelled_steps,
        "false_flag_rate_per_labelled_step": (
            proportion(false_flags_on_labelled_sound, labelled_steps).as_dict()
            if labelled_steps
            else None
        ),
        "false_flag_rate_per_trace": None,
        "false_flag_rate_per_trace_note": (
            "NOT COMPUTED. B4 #4's second clause needs all steps of the five traces "
            "human-labelled (M2-15, dropped by amendment 002). Multiplying the "
            "per-labelled-step rate by the mean trace length would state a per-trace "
            "figure the labels do not support -- that is the conversion SS1.3.1 says to "
            "STATE rather than PERFORM."
        ),
        "per_trace": per_trace,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n")

    def show(label: str, est: dict | None) -> None:
        if not est:
            print(f"  {label:<24} not computable (no flags)")
            return
        print(
            f"  {label:<24} {est['value']:.3f}  "
            f"[{est['ci_low']:.3f}, {est['ci_high']:.3f}]  n={est['n']}"
        )

    print("\npooled judge precision · M2-7 · B4 #4")
    print("=" * 78)
    show("precision (strict)", doc["precision_strict"])
    show("precision (symmetric)", doc["precision_symmetric"])
    print(f"  flags over the pool      {flags_strict}")
    print(f"  seeded reports read      {len(seeded_reports)}")
    print()
    show("false flags / lab. step", doc["false_flag_rate_per_labelled_step"])
    print(f"  false flags on human-`sound` steps  {false_flags_on_labelled_sound}")
    print("  per-TRACE rate            NOT COMPUTED -- needs M2-15 (dropped, amendment 002)")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
