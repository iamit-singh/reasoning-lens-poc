#!/usr/bin/env python3
"""Draw the enriched-60 — the second half of C5.1's two-part frame (M2-14).

    make draw-enriched          # appends the enriched draw to calibration/sampling.json
    make draw-enriched ARGS="--force"   # redraw. Refuses if enriched labels exist.

**The random-90 carries the published kappa. This half does not, and that asymmetry is
the whole reason the frame has two parts.** A uniform draw over a corpus that is 82%
`linear` gives per-class F1 almost nothing to work with on the rare classes, so C5.1
over-samples them deliberately — and then keeps them out of the number whose sampling has
to be independent of anything the classifier did.

Why the predictions come from **v0**, deliberately
--------------------------------------------------
M2-14's card is explicit: enrich from the *un-tuned* classifier. Enriching from the tuned
one would couple the rare-class evaluation set to the tuned model's own error structure —
the classifier would be scored on precisely the steps it had learned to call non-linear.
Pre-iteration enrichment is the methodologically better choice and it happens to be the
schedulable one, since M2-3 needs dev labels that do not exist yet.

**Blindness is unaffected.** The draw uses predictions; `label.py` never shows them.

The single-pass caveat, stated here rather than discovered later
---------------------------------------------------------------
These predictions come from **one pass** of a **non-deterministic** classifier. ADR-010's
amendment is the cautionary tale: `backtracking` measured 0 on one pass and 2.0% over
twelve, firing between 1 and 15 times per run. So a single pass is a *weak instrument for
finding* rare-class candidates, and the shortfall this script reports is partly a property
of the sampler rather than only of the corpus.

That is recorded in the draw and left as a named option rather than silently adopted: the
plan's pre-decided action for a class that cannot reach 15 is trigger **t13** — *label what
exists, publish the actual n with a wide CI, never backfill from the random pool* — and
this script does exactly that. A multi-pass union enrichment would find more candidates
and is a change to the sampling frame, which is the reviewer's call, not this script's.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))
sys.path.insert(0, str(ROOT / "scripts"))

from draw_sample import LABELLED_KINDS, population  # noqa: E402
from rlens.versions import PROMPT_BUNDLE_VERSION  # noqa: E402

REPORTS = ROOT / "out/reports"
SAMPLING = ROOT / "calibration/sampling.json"
LABELS = ROOT / "calibration/labels"

#: C5.1's enrichment target: up to this many per rare class.
PER_CLASS = 15

#: Every class that is not the majority class. `linear` is 82% of the corpus and needs no
#: help; these four are why the enriched half exists at all.
RARE_CLASSES = ("verification", "subgoal_setting", "backtracking", "backward_chaining")

#: Committed before the draw, like the random-90's. A draw that cannot be reproduced from
#: its seed is not a sample, it is a selection.
ENRICHED_SEED = 20261014


def predictions() -> dict[str, str]:
    """The v0 behaviour label per step, read from the cached full-corpus pass.

    Keyed by `step_id`, which C3.2 calls the join key for every label ever written — and
    which M1-10 found was *not* unique until it was fixed. A duplicate here would silently
    overwrite one step's prediction with another's, so it is asserted rather than assumed.
    """
    preds: dict[str, str] = {}
    for path in sorted(REPORTS.glob("*.json")):
        report = json.loads(path.read_text())
        for arm in report["arms"]:
            for step in arm.get("steps") or []:
                if step.get("kind") not in LABELLED_KINDS or not step.get("behavior"):
                    continue
                sid = step["step_id"]
                if sid in preds:
                    raise SystemExit(
                        f"duplicate step_id {sid!r} across reports. The join key is not "
                        f"unique, so a prediction would be attributed to the wrong step."
                    )
                preds[sid] = step["behavior"]["label"]
    return preds


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=ENRICHED_SEED)
    ap.add_argument("--per-class", type=int, default=PER_CLASS)
    ap.add_argument("--force", action="store_true", help="redraw even if a draw exists")
    args = ap.parse_args(argv)

    if not REPORTS.is_dir() or not any(REPORTS.glob("*.json")):
        print(
            f"no reports at {REPORTS}. Run `make report` first -- the enriched draw needs "
            f"the v0 classifier's predictions over the whole corpus.",
            file=sys.stderr,
        )
        return 2

    record = json.loads(SAMPLING.read_text())
    if not record.get("draw", {}).get("ordered_step_ids"):
        print(
            "no random-90 draw in calibration/sampling.json. The enriched half is drawn "
            "from the pool REMAINING after it, so it cannot be drawn first.",
            file=sys.stderr,
        )
        return 2
    if record.get("enriched") and not args.force:
        print(
            f"an enriched draw already exists (seed {record['enriched'].get('seed')}). "
            f"Re-drawing after labelling has begun re-labels every affected step. "
            f"Pass --force if that is intended.",
            file=sys.stderr,
        )
        return 2

    written = sorted(LABELS.glob("*.jsonl"))
    if written and args.force:
        print(
            f"--force refused: {len(written)} label file(s) already exist "
            f"({', '.join(p.name for p in written)}). A redraw now would mix two draws in "
            f"one dataset and nothing downstream could tell which row came from which.",
            file=sys.stderr,
        )
        return 2

    pool = population()
    preds = predictions()
    frame = {s["step_id"] for s in pool}
    if frame != set(preds):
        only_pool, only_pred = len(frame - set(preds)), len(set(preds) - frame)
        print(
            f"the prediction set and the sampling frame disagree ({only_pool} steps with "
            f"no prediction, {only_pred} predictions outside the frame). The reports are "
            f"stale against the segmenter or the corpus. Re-run `make report`.",
            file=sys.stderr,
        )
        return 2

    drawn_90 = set(record["draw"]["ordered_step_ids"])
    remaining = [s for s in pool if s["step_id"] not in drawn_90]
    base = collections.Counter(preds[s["step_id"]] for s in remaining)

    rng = random.Random(args.seed)
    selected: list[str] = []
    per_class: dict[str, dict[str, object]] = {}
    for cls in RARE_CLASSES:
        candidates = sorted(s["step_id"] for s in remaining if preds[s["step_id"]] == cls)
        rng.shuffle(candidates)
        take = candidates[: args.per_class]
        selected.extend(take)
        per_class[cls] = {
            "candidates_in_remaining_pool": len(candidates),
            "selected": len(take),
            "short_of_target": max(0, args.per_class - len(take)),
            "base_rate_in_remaining_pool": round(base.get(cls, 0) / len(remaining), 4),
        }

    target = args.per_class * len(RARE_CLASSES)
    short = [c for c in RARE_CLASSES if per_class[c]["short_of_target"]]

    # The enrichment factor is the point of the whole exercise, so it is recorded as a
    # number rather than described. Share of non-linear in the enriched draw over its
    # share in the pool the draw came from.
    nonlinear_in_pool = sum(base.get(c, 0) for c in RARE_CLASSES) / len(remaining)
    factor = (1.0 / nonlinear_in_pool) if nonlinear_in_pool else None

    record["enriched"] = {
        "owner": "M2-14 (W5)",
        "seed": args.seed,
        "drawn_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": _git_sha(),
        "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
        "classifier": "v0 -- UN-TUNED, deliberately (M2-14). Enriching from the tuned "
        "classifier would couple the rare-class evaluation set to the tuned model's own "
        "error structure: it would be scored on precisely the steps it had learned to "
        "call non-linear.",
        "method": (
            f"For each of {'/'.join(RARE_CLASSES)}: take every step in the pool REMAINING "
            f"after the random-90 whose v0 prediction is that class, sort by step_id, "
            f"shuffle with random.Random({args.seed}), take up to {args.per_class}. "
            f"Sorted before the shuffle so the result depends on the seed alone."
        ),
        "population_size": len(pool),
        "remaining_pool_size": len(remaining),
        "target": target,
        "selected_total": len(selected),
        "short_of_target_total": target - len(selected),
        "classes_that_could_not_reach_target": short,
        "per_class": per_class,
        "enrichment_factor": round(factor, 2) if factor else None,
        "enrichment_factor_note": (
            f"Non-linear steps are {nonlinear_in_pool:.1%} of the remaining pool; the "
            f"enriched draw is 100% non-linear by construction, so the enrichment is "
            f"{factor:.2f}x on the non-linear classes as a group."
            if factor
            else "No non-linear predictions in the remaining pool."
        ),
        "trigger_t13": (
            "FIRED. "
            + ", ".join(
                f"{c} reached {per_class[c]['selected']} of {args.per_class}" for c in short
            )
            + ". Pre-decided action: label what exists and publish the actual n with a wide "
            "interval. NEVER backfill from the random pool -- that would take steps out of "
            "the half that carries the published kappa to prop up the half that does not."
            if short
            else "not fired -- every rare class reached its target."
        ),
        "single_pass_caveat": (
            "These predictions are ONE PASS of a NON-DETERMINISTIC classifier. ADR-010's "
            "amendment measured `backtracking` at 0 on one pass and 2.0% over twelve, "
            "firing 1-15 times per run. So a shortfall here is partly a property of the "
            "sampler and not only of the corpus. A multi-pass union would find more "
            "candidates; it is a change to the sampling frame and is the reviewer's call."
        ),
        "excluded_from": "the random-90, and therefore from the published held-out kappa. "
        "These ids join dev-100 (C5.1: dev = random 1-40 + enriched 60).",
        "ordered_step_ids": selected,
    }
    SAMPLING.write_text(json.dumps(record, indent=2) + "\n")

    print(f"enriched draw, seed {args.seed}, bundle {PROMPT_BUNDLE_VERSION}")
    print(f"  pool {len(pool)} steps; {len(remaining)} remain after the random-90")
    for cls in RARE_CLASSES:
        p = per_class[cls]
        flag = "  <-- SHORT" if p["short_of_target"] else ""
        print(
            f"  {cls:20s} {p['selected']:>2} of {args.per_class}"
            f"  (candidates {p['candidates_in_remaining_pool']}){flag}"
        )
    print(f"  total {len(selected)} of {target}; enrichment {factor:.2f}x on non-linear")
    if short:
        print(f"\nTRIGGER t13 FIRED: {', '.join(short)} cannot reach {args.per_class}.")
        print("Label what exists; publish the actual n with a wide CI. Do NOT backfill")
        print("from the random pool -- see calibration/sampling.json for the record.")
    print(f"\n  -> {SAMPLING}")
    print("\nCOMMIT THIS FILE BEFORE WRITING THE FIRST ENRICHED LABEL (Hazard 2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
