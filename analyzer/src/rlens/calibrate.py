"""`make calibrate` — the numbers the public page renders verbatim. C5.5, M2-13.

    make calibrate                 # dev set only. Safe, and the default
    make calibrate ARGS="--final"  # reads the held-out 50. Refuses unless frozen
    make calibrate ARGS="--json"   # the report on stdout

Writes `calibration/results/latest.json`, which FE-6 renders **with zero hard-coded
numbers**. That is the whole contract: if a number is on the calibration page, it came out
of this file, and if it is not in this file the page cannot show it.

Two guards are part of the CLI rather than conventions
------------------------------------------------------
1. **`--final` is required to read `heldout-50.jsonl`, and refuses unless the prompt bundle
   is frozen** (C5.4). The held-out set is opened once. A tool that would read it by
   default turns "opened once" into a promise somebody has to keep under time pressure,
   and C5.4 exists because that promise is not keepable.
2. **Every number carries its n and its interval.** `rlens.metrics` makes this structural —
   there is no way to get a bare float out of it — so this module cannot emit one by
   accident.

What it joins, and why the join key had to be fixed first
---------------------------------------------------------
Human labels live in `calibration/labels/*.jsonl`; classifier predictions live in the
reports under `out/reports/`. They are joined on `step_id`, which is the reason M1-10 had
to fix `step_id` uniqueness before any of this could work: the join silently collapsed 310
steps into 155 keys, and a κ computed over that would have looked entirely normal.

**It runs on partial label files.** In W5 there are 40 of 100 dev labels, and a tool that
crashed or refused until the set was complete would be unavailable during the only weeks
anybody needs it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
from collections import defaultdict
from typing import Any

from rlens.metrics import BEHAVIOR_CLASSES, SOUNDNESS_CLASSES, Agreement, agreement
from rlens.versions import ANALYZER_VERSION, PROMPT_BUNDLE_VERSION

#: Resolved from the checkout root, not the working directory. `rlens.runner.paths` solves
#: the same problem for the bank; this module sits below the runner in the layer contract
#: and cannot import it, so the two-line version lives here.
_ROOT = pathlib.Path(__file__).resolve().parents[3]

LABELS_DIR = _ROOT / "calibration/labels"
RESULTS_DIR = _ROOT / "calibration/results"
REPORTS_DIR = _ROOT / "out/reports"
SAMPLING_FILE = _ROOT / "calibration/sampling.json"

#: C5.4's freeze marker. Its presence means the held-out labels are sealed and the prompt
#: bundle that will be scored against them is pinned.
FREEZE_FILE = LABELS_DIR / "HELDOUT_FREEZE"
HELDOUT_FILE = LABELS_DIR / "heldout-50.jsonl"

#: C5.1/§2.2: the random-90 splits at 40. Positions 1-40 are M1-11's dev pass; 41-90 are
#: the held-out set that carries the published kappa.
HELDOUT_SPLIT_AT = 40


def heldout_step_ids() -> frozenset[str]:
    """The held-out half of the random draw, by `step_id`.

    **The C5.4 exclusion is keyed on the draw, not on a filename.** It used to be keyed on
    the filename alone, and that is not a guard: the labelling tool appends to
    `<annotator>.jsonl`, so a pass that ran straight through position 40 put 50 held-out
    rows in `amit.jsonl`, where the default `make calibrate` counted them as dev. The same
    hole was waiting for the second annotator in W6 — `annotator-2.md` tells Ankit his file
    is `labels/<annotator>.jsonl`, and he labels *nothing but* the held-out 50, so
    `ankit.jsonl` would have leaked the entire set.

    Returns an empty set when the draw is missing, and the filename rule below still
    applies — the two checks are deliberately redundant.
    """
    if not SAMPLING_FILE.is_file():
        return frozenset()
    draw = json.loads(SAMPLING_FILE.read_text()).get("draw", {})
    return frozenset(draw.get("ordered_step_ids", [])[HELDOUT_SPLIT_AT:])


class CalibrationRefused(RuntimeError):
    """A guard fired. The message names what to do; it is never advice to try again."""


def _short(path: pathlib.Path) -> str:
    """Repo-relative where possible, absolute otherwise.

    `Path.relative_to` RAISES when the path is outside the root, and these paths are only
    ever used to build a refusal message. An error message that throws while explaining a
    refusal replaces a clear message with a stack trace — found by the first test that
    pointed the module at a scratch directory.
    """
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


# ------------------------------------------------------------------------ loading
def load_labels(*, include_heldout: bool) -> list[dict[str, Any]]:
    """Every human label, newest-wins per (annotator, step_id).

    Re-labelling is allowed and appends — `label.py` never rewrites a line — so the last
    row for a pair is the live one. Taking the first would silently score an annotator
    against a judgement they had already corrected.
    """
    if not LABELS_DIR.is_dir():
        return []
    held = frozenset() if include_heldout else heldout_step_ids()
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(LABELS_DIR.glob("*.jsonl")):
        if path.name == HELDOUT_FILE.name and not include_heldout:
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            # Whatever file it arrived in. A held-out step is held out.
            if row["step_id"] in held:
                continue
            row.setdefault("source_file", path.name)
            latest[(row.get("annotator", path.stem), row["step_id"])] = row
    return list(latest.values())


def load_predictions() -> dict[str, dict[str, Any]]:
    """Classifier predictions by `step_id`, read from committed reports.

    Reports rather than a live classifier run, deliberately: `make report` already replays
    from cassettes, so calibration is deterministic, offline and free. A version that
    called the model would make the published number depend on the day it was computed.
    """
    predictions: dict[str, dict[str, Any]] = {}
    if not REPORTS_DIR.is_dir():
        return predictions
    for path in sorted(REPORTS_DIR.glob("*.report.json")):
        report = json.loads(path.read_text())
        for arm in report.get("arms", []):
            for step in arm.get("steps", []):
                behavior = step.get("behavior") or {}
                validity = step.get("validity") or {}
                predictions[step["step_id"]] = {
                    "behavior": behavior.get("label"),
                    "soundness": validity.get("verdict"),
                    "item_id": report["item"]["id"],
                    "strategy": arm["strategy"],
                }
    return predictions


# ------------------------------------------------------------------------ scoring
def _paired(
    labels: list[dict[str, Any]], predictions: dict[str, dict[str, Any]], field: str, key: str
) -> tuple[list[str], list[str], list[str]]:
    """(human, classifier, step_ids) over steps that have both, and a usable value."""
    human, machine, ids = [], [], []
    for row in labels:
        truth = row.get(field)
        predicted = (predictions.get(row["step_id"]) or {}).get(key)
        if truth and predicted:
            human.append(truth)
            machine.append(predicted)
            ids.append(row["step_id"])
    return human, machine, ids


def inter_annotator(labels: list[dict[str, Any]], field: str) -> Agreement | None:
    """Human vs human, over steps two people both labelled (B4 #1).

    **This is the number that separates a measurement from one person asserting their own
    labels are correct**, and it is the one that is not computable with a single annotator
    — not harder, not noisier: not computable. Returns None rather than a zero when there
    is no overlap, because a zero would read as "they disagreed".
    """
    by_step: dict[str, dict[str, str]] = defaultdict(dict)
    for row in labels:
        value = row.get(field)
        if value:
            by_step[row["step_id"]][row.get("annotator", "?")] = value

    a_labels, b_labels = [], []
    for votes in by_step.values():
        if len(votes) >= 2:
            names = sorted(votes)
            a_labels.append(votes[names[0]])
            b_labels.append(votes[names[1]])
    if len(a_labels) < 2:
        return None
    classes = BEHAVIOR_CLASSES if field == "behavior_label" else SOUNDNESS_CLASSES
    return agreement(a_labels, b_labels, classes)


def build_results(*, final: bool) -> dict[str, Any]:
    """Everything C5.5 asks for, over whatever labels exist today."""
    labels = load_labels(include_heldout=final)
    predictions = load_predictions()

    behavior_h, behavior_m, _ = _paired(labels, predictions, "behavior_label", "behavior")
    sound_h, sound_m, _ = _paired(labels, predictions, "soundness_label", "soundness")

    classifier_behavior = (
        agreement(behavior_h, behavior_m, BEHAVIOR_CLASSES) if behavior_h else None
    )
    classifier_soundness = agreement(sound_h, sound_m, SOUNDNESS_CLASSES) if sound_h else None
    iaa_behavior = inter_annotator(labels, "behavior_label")
    iaa_soundness = inter_annotator(labels, "soundness_label")

    annotators = sorted({row.get("annotator", "?") for row in labels})
    skipped = sum(1 for row in labels if row.get("skipped"))

    return {
        "_README": (
            "Written by `make calibrate` (M2-13). FE-6 renders this VERBATIM with zero "
            "hard-coded numbers. A null is a real state meaning 'not measured yet' and "
            "must render as such -- never as 0, and never by hiding the row."
        ),
        "run": {
            "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mode": "final" if final else "dev",
            "analyzer_version": ANALYZER_VERSION,
            "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
            "analyzer_backend": os.environ.get("ANALYZER_BACKEND", "hybrid"),
            "judge_triage_pin": os.environ.get("MODEL_ANALYZE") or None,
            "labels_loaded": len(labels),
            "labels_skipped_by_annotator": skipped,
            "annotators": annotators,
            "predictions_loaded": len(predictions),
            "steps_joined_behavior": len(behavior_h),
            "steps_joined_soundness": len(sound_h),
        },
        # C3.4: "exactly the measurement_context block above, plus n, CIs and run metadata".
        "measurement_context": {
            "classifier_kappa_heldout": (
                classifier_behavior.kappa.as_dict() if final and classifier_behavior else None
            ),
            "classifier_kappa_dev": (
                classifier_behavior.kappa.as_dict() if not final and classifier_behavior else None
            ),
            "majority_class_baseline": (
                classifier_behavior.majority_baseline.as_dict() if classifier_behavior else None
            ),
            "per_class_f1": (
                {c.label: c.f1 for c in classifier_behavior.per_class}
                if classifier_behavior
                else None
            ),
            # M2-6, M2-7, M2-8 and M2-9 fill these. Null is the honest Month-1/W5 value.
            "judge_precision": None,
            "judge_recall": None,
            "consistency_fp_rate": None,
            "n_heldout": len(behavior_h) if final else None,
            "n_dev": len(behavior_h) if not final else None,
            "calibration_run_id": f"cal-{dt.datetime.now(dt.UTC).strftime('%Y-%m-%d')}",
        },
        "inter_annotator": {
            "behavior": iaa_behavior.as_dict() if iaa_behavior else None,
            "soundness": iaa_soundness.as_dict() if iaa_soundness else None,
            "note": (
                "Human vs human. NOT COMPUTABLE with a single annotator -- not harder, not "
                "noisier: not computable. A null here means the second annotator has not "
                "labelled yet, and the headline claim cannot be made until they have."
            ),
        },
        "classifier_vs_human": {
            "behavior": classifier_behavior.as_dict() if classifier_behavior else None,
            "soundness": classifier_soundness.as_dict() if classifier_soundness else None,
        },
        "faithfulness": {
            "note": "M2-9. See docs/spikes/S4-cues.md and ADR-009 -- 0 of 48 trials flipped.",
            "flips": None,
            "verbalisation_rate": None,
        },
        "seeded_errors": {"note": "M2-6.", "recall_by_mutation_type": None},
    }


# ------------------------------------------------------------------------ the guards
def check_final_allowed() -> None:
    """C5.4. **The held-out set is opened once, and this is what makes that true.**"""
    if not HELDOUT_FILE.exists():
        raise CalibrationRefused(
            f"--final needs {_short(HELDOUT_FILE)}, which does not exist yet. "
            f"The held-out 50 are labelled in M2-1a."
        )
    if not FREEZE_FILE.exists():
        raise CalibrationRefused(
            f"--final refused: {_short(FREEZE_FILE)} is absent, so the prompt "
            f"bundle is not frozen (C5.4). Scoring the held-out set against an unfrozen "
            f"bundle means the number can be re-rolled until it is liked, which is the one "
            f"thing the held-out set exists to prevent. Freeze first (M2-16)."
        )
    frozen = FREEZE_FILE.read_text().strip()
    if PROMPT_BUNDLE_VERSION not in frozen:
        raise CalibrationRefused(
            f"--final refused: the prompts have changed since the freeze. "
            f"HELDOUT_FREEZE records {frozen!r}; the bundle is now "
            f"{PROMPT_BUNDLE_VERSION!r}. Re-freezing is a deliberate act (M2-16), and the "
            f"published number belongs to the bundle named in the freeze."
        )


# ------------------------------------------------------------------------ CLI
def _render(results: dict[str, Any]) -> str:
    run = results["run"]
    lines = [
        "",
        f"calibration · {run['mode']} · bundle {run['prompt_bundle_version']} · "
        f"{run['labels_loaded']} labels from {run['annotators'] or '(nobody yet)'}",
        "=" * 78,
    ]
    cvh = results["classifier_vs_human"]["behavior"]
    if not cvh:
        lines += [
            "  classifier vs human: NOT COMPUTABLE -- no step has both a human label and a",
            "    prediction. Label some steps (`make label`) and generate reports",
            "    (`make report ARGS=--all`).",
        ]
    else:
        kappa, base = cvh["kappa"], cvh["majority_class_baseline"]
        ci = (
            f"[{kappa['ci_low']:.3f}, {kappa['ci_high']:.3f}]"
            if kappa["ci_low"] is not None
            else "CI not computable"
        )
        value = f"{kappa['value']:.3f}" if kappa["value"] is not None else "undefined"
        lines += [
            f"  behavior kappa        {value}  {ci}  n={kappa['n']}",
            f"  majority baseline     {base['value']:.3f}  ({base['note']})",
            f"  agreement - baseline  {cvh['agreement_over_baseline_pp']:+.1f} pp",
            f"  classes absent        {cvh['classes_absent_from_this_sample'] or 'none'}",
            "",
            f"  {'class':20s} {'F1':>8s} {'support':>8s} {'predicted':>10s}",
        ]
        for label, score in cvh["per_class"].items():
            f1 = f"{score['f1']:.3f}" if score["f1"] is not None else "  n/a"
            lines.append(f"  {label:20s} {f1:>8s} {score['support']:8d} {score['predicted']:10d}")
    iaa = results["inter_annotator"]["behavior"]
    iaa_value = iaa["kappa"]["value"] if iaa else "NOT COMPUTABLE -- one annotator"
    lines += ["", f"  inter-annotator kappa {iaa_value}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rlens-calibrate", description=__doc__)
    ap.add_argument("--final", action="store_true", help="read the held-out 50 (C5.4 guarded)")
    ap.add_argument("--dev", action="store_true", help="dev set only (the default)")
    ap.add_argument("--json", action="store_true", help="print the results instead of a summary")
    ap.add_argument("--out", default=str(RESULTS_DIR / "latest.json"))
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.final:
        try:
            check_final_allowed()
        except CalibrationRefused as exc:
            sys.stderr.write(f"{exc}\n")
            return 2

    results = build_results(final=args.final)
    body = json.dumps(results, indent=2, sort_keys=True) + "\n"

    if args.json:
        sys.stdout.write(body)
    else:
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(_render(results))
        print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
