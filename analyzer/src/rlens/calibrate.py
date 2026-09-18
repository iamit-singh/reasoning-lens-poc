"""`make calibrate` — the numbers the public page renders verbatim. C5.5, M2-13.

    make calibrate                 # dev set only. Safe, and the default
    make calibrate ARGS="--iaa"    # + B4 #1, the human-vs-human kappa on the double labels
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

Why `--iaa` is a third mode rather than a corner of the other two
----------------------------------------------------------------
B4 #1 is computed on the 50 **held-out** steps, because that is the only half both
annotators labelled — `annotator-2.md` sends the second annotator there and nowhere else.
So the C5.4 exclusion, which is correct, removes every step the agreement is computed from,
and the default run reports it NOT COMPUTABLE with both passes sitting in the file. `--final`
would see them, but `--final` is the held-out *scoring* read: it needs M2-16's freeze, and
it produces the published classifier kappa — the one number M2-2's ordering control says
must not exist yet.

`--iaa` is the narrow thing in between: it widens **only** the label set that human-vs-human
reads. The classifier join keeps the dev set, `classifier_kappa_heldout` stays null, and no
freeze is required, because human-vs-human touches no classifier output — §8.1 P1's own
wording, and the reason the breakdown lists M2-2 as reading the held-out labels without
counting as the C5.4 read.

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

from rlens.metrics import (
    BEHAVIOR_CLASSES,
    SOUNDNESS_CLASSES,
    Agreement,
    agreement,
    proportion,
)
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


def unmatched(
    labels: list[dict[str, Any]], predictions: dict[str, dict[str, Any]], field: str, key: str
) -> list[str]:
    """Labelled steps the classifier produced no usable prediction for.

    **This exists because the join silently shrinks the denominator, and that was measured
    rather than imagined.** A variance pass on bundle `e8952d4d3c51` came back κ -0.032 on
    `n=32` while the header line of the same output read *"40 labels"*. Eight labelled steps
    had a step entry with a **null behavior** — a degraded or repaired classifier call
    leaves the step in the report and the label off it — so `_paired` dropped them and κ
    was computed over 80% of the dev set with nothing raised.

    The reason this matters more than a warning usually would: **M2-17 runs once.** A
    degraded arm on the day of the `--final` read would publish the headline κ over 42 of
    50 held-out steps, and the only trace of it would be two fields in a JSON file that
    disagree. `n` was always reported honestly; nothing ever *reconciled* it.
    """
    return [
        row["step_id"]
        for row in labels
        if row.get(field) and not (predictions.get(row["step_id"]) or {}).get(key)
    ]


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


AUX_PRECISION = RESULTS_DIR / "pooled-precision.json"
AUX_CONSISTENCY = RESULTS_DIR / "consistency-fp.json"
AUX_SEEDED = _ROOT / "docs/spikes/M2-6-raw/m2-6-seeded.json"
AUX_PANEL = _ROOT / "faithfulness/panel.json"


def _json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError):
        return None


def auxiliary() -> dict[str, Any]:
    """The measured numbers that live in their own files, joined in here.

    **This exists because the calibration page renders `latest.json` VERBATIM.** M2-7's
    precision, M2-8's FP rate and M2-6's recall were all measured and all sat in separate
    files, so the public page said *"not yet measured"* for three numbers this project had
    measured. A page that understates is not automatically safe: it was telling a reader the
    instrument is less calibrated than it is, which is a false statement about the evidence.

    **Read, never recomputed.** Each figure is copied from the artefact its own task wrote,
    so there is exactly one place each number is produced. A second computation here would
    eventually disagree with the first, and the one on the public page is the one nobody
    re-derives.

    Missing files give None, which renders as "not yet measured" -- the correct answer when
    the task has not run.
    """
    out: dict[str, Any] = {
        "judge_precision": None,
        "judge_recall": None,
        "consistency_fp_rate": None,
        "seeded": None,
        "faithfulness": None,
    }
    prec = _json(AUX_PRECISION)
    if prec:
        # The STRICT reading -- C5.6 read literally -- is what the page publishes, because
        # it is the conservative one. The symmetric reading is in the file beside it and in
        # the G2 report; the page links to both rather than choosing the kinder number.
        out["judge_precision"] = prec.get("precision_strict")
    cons = _json(AUX_CONSISTENCY)
    if cons and cons.get("n_traces"):
        out["consistency_fp_rate"] = cons.get("estimate")
    seeded = _json(AUX_SEEDED)
    if seeded:
        cases = seeded.get("cases") or []
        graded = [c for c in cases if c.get("hit") is not None]
        # **Triage-alone, because that is the shipped configuration** (ADR-012, finding 16).
        # `hit_triage_only` is absent on records written before the tier was wired, and the
        # fallback to `hit` is correct for those: escalation had not run.
        hits = [c for c in graded if c.get("hit_triage_only", c.get("hit"))]
        if graded:
            out["judge_recall"] = proportion(
                len(hits), len(graded), note="seeded errors, correct-step rule, triage-alone"
            ).as_dict()
        out["seeded"] = {
            "recall_by_mutation_type": _by_type(graded),
            "escalation_delta_cases": (
                len([c for c in graded if c.get("hit")]) - len(hits)
                if any(c.get("escalation") for c in graded)
                else None
            ),
        }
    panel = _json(AUX_PANEL)
    if panel:
        out["faithfulness"] = panel.get("headline")
    return out


def _by_type(graded: list[dict[str, Any]]) -> dict[str, str]:
    """Hit/miss with n, never a bare percentage -- a "100%" over n = 1 is not a percentage."""
    buckets: dict[str, list[bool]] = defaultdict(list)
    for case in graded:
        buckets[case.get("expected_error_type") or "?"].append(
            bool(case.get("hit_triage_only", case.get("hit")))
        )
    return {k: f"{sum(v)}/{len(v)}" for k, v in sorted(buckets.items())}


def build_results(*, final: bool, iaa_heldout: bool = False) -> dict[str, Any]:
    """Everything C5.5 asks for, over whatever labels exist today.

    Two label sets, deliberately not one. `labels` is what the classifier is scored
    against and stays under C5.4's exclusion; `iaa_labels` is what human-vs-human reads.
    Keeping them as separate names is the guard — `_paired` is only ever handed `labels`,
    so widening the agreement set cannot widen the scoring set by accident.
    """
    labels = load_labels(include_heldout=final)
    iaa_labels = load_labels(include_heldout=True) if (final or iaa_heldout) else labels
    predictions = load_predictions()
    aux = auxiliary()

    # **In `--final`, the published kappa is the HELD-OUT 50 and nothing else.**
    #
    # `load_labels(include_heldout=True)` returns every row: the dev 40, plus the held-out
    # 50 from EACH annotator. Scoring all of them -- which is what this did on the first
    # `--final` run -- produces n=140: the dev set folded into the number that is supposed
    # to be untouched by tuning, and every held-out step counted twice because two people
    # labelled it. Both halves of that are wrong in the same direction: they dilute the
    # held-out kappa with steps the prompt was tuned against.
    #
    # So the scoring set is restricted to the held-out draw and split BY ANNOTATOR. Two
    # kappas are published rather than one, and that is finding 14's requirement rather
    # than caution: the two annotators disagree on exactly 2 of 50 steps, the classifier
    # agrees with a DIFFERENT one on each, and no adjudication exists (amendment 002). A
    # single number would require choosing whose labels are ground truth on precisely the
    # two steps where the choice changes the answer -- after the predictions are known.
    held_ids = heldout_step_ids()
    scoring_sets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if final:
        for row in labels:
            if row["step_id"] in held_ids:
                scoring_sets[row.get("annotator", "?")].append(row)
    if not scoring_sets:
        scoring_sets["*"] = labels
    primary = sorted(scoring_sets)[0]

    per_annotator = {}
    for who, rows in sorted(scoring_sets.items()):
        b_h, b_m, _ = _paired(rows, predictions, "behavior_label", "behavior")
        s_h, s_m, _ = _paired(rows, predictions, "soundness_label", "soundness")
        per_annotator[who] = {
            "behavior": agreement(b_h, b_m, BEHAVIOR_CLASSES).as_dict() if b_h else None,
            "soundness": agreement(s_h, s_m, SOUNDNESS_CLASSES).as_dict() if s_h else None,
            "n": len(b_h),
        }

    scored_rows = scoring_sets[primary]
    behavior_h, behavior_m, _ = _paired(scored_rows, predictions, "behavior_label", "behavior")
    sound_h, sound_m, _ = _paired(scored_rows, predictions, "soundness_label", "soundness")

    classifier_behavior = (
        agreement(behavior_h, behavior_m, BEHAVIOR_CLASSES) if behavior_h else None
    )
    classifier_soundness = agreement(sound_h, sound_m, SOUNDNESS_CLASSES) if sound_h else None
    iaa_behavior = inter_annotator(iaa_labels, "behavior_label")
    iaa_soundness = inter_annotator(iaa_labels, "soundness_label")

    annotators = sorted({row.get("annotator", "?") for row in iaa_labels})
    skipped = sum(1 for row in labels if row.get("skipped"))
    unmatched_behavior = unmatched(scored_rows, predictions, "behavior_label", "behavior")
    unmatched_soundness = unmatched(scored_rows, predictions, "soundness_label", "soundness")

    return {
        "_README": (
            "Written by `make calibrate` (M2-13). FE-6 renders this VERBATIM with zero "
            "hard-coded numbers. A null is a real state meaning 'not measured yet' and "
            "must render as such -- never as 0, and never by hiding the row."
        ),
        "run": {
            "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mode": "final" if final else ("dev+iaa" if iaa_heldout else "dev"),
            "analyzer_version": ANALYZER_VERSION,
            "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
            "analyzer_backend": os.environ.get("ANALYZER_BACKEND", "hybrid"),
            "judge_triage_pin": os.environ.get("MODEL_ANALYZE") or None,
            "labels_loaded": len(iaa_labels),
            # What the classifier numbers were computed against. It differs from
            # `labels_loaded` only in `--iaa`, and that difference is the point of the mode.
            "labels_scored": len(scored_rows),
            "scored_against_annotator": primary,
            "classifier_vs_each_annotator": per_annotator,
            "labels_skipped_by_annotator": skipped,
            "annotators": annotators,
            "predictions_loaded": len(predictions),
            "steps_joined_behavior": len(behavior_h),
            "steps_joined_soundness": len(sound_h),
            # The reconciliation. `labels_scored` and `steps_joined_*` could always
            # disagree; nothing ever said so out loud. See `unmatched()`.
            "labels_unmatched_behavior": len(unmatched_behavior),
            "labels_unmatched_soundness": len(unmatched_soundness),
            "unmatched_step_ids": sorted(set(unmatched_behavior) | set(unmatched_soundness)),
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
            # M2-6, M2-7, M2-8 and M2-9 fill these, from their own artefacts. Null still
            # means "that task has not run" -- see `auxiliary()`.
            "judge_precision": aux["judge_precision"],
            "judge_recall": aux["judge_recall"],
            "consistency_fp_rate": aux["consistency_fp_rate"],
            "n_heldout": len(behavior_h) if final else None,
            "n_dev": len(behavior_h) if not final else None,
            "calibration_run_id": f"cal-{dt.datetime.now(dt.UTC).strftime('%Y-%m-%d')}",
        },
        "inter_annotator": {
            "behavior": iaa_behavior.as_dict() if iaa_behavior else None,
            "soundness": iaa_soundness.as_dict() if iaa_soundness else None,
            "annotators": annotators,
            "source": "heldout-50" if (final or iaa_heldout) else "dev",
            "note": (
                "Human vs human. NOT COMPUTABLE with a single annotator -- not harder, not "
                "noisier: not computable. A null here means the second annotator has not "
                "labelled yet, and the headline claim cannot be made until they have. "
                "Computed on the double-labelled steps only; it reads no classifier output, "
                "which is why it does not wait on the held-out freeze."
            ),
        },
        "classifier_vs_human": {
            "behavior": classifier_behavior.as_dict() if classifier_behavior else None,
            "soundness": classifier_soundness.as_dict() if classifier_soundness else None,
        },
        "faithfulness": {
            "note": "M2-9. See docs/spikes/S4-cues.md and ADR-009.",
            "headline": aux["faithfulness"],
        },
        "seeded_errors": {
            "note": (
                "M2-6, correct-step rule. Recall is TRIAGE-ALONE, the shipped configuration: "
                "the escalation tier was measured and declined (ADR-012, finding 16)."
            ),
            **(aux["seeded"] or {"recall_by_mutation_type": None}),
        },
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
    miss = run.get("unmatched_step_ids") or []
    if miss:
        lines += [
            f"  !! COVERAGE: {run['labels_scored']} labels loaded, "
            f"{run['steps_joined_behavior']} scored -- {len(miss)} labelled step(s) have no",
            "     classifier prediction, so every number below is over the SMALLER set.",
            "     A degraded or repaired classifier call leaves the step in the report with a",
            "     null label; the join drops it. First few: " + ", ".join(miss[:3]),
            "",
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
    block = results["inter_annotator"]
    lines.append("")
    if not block["behavior"]:
        # **Naming the reason matters.** The same null covers "nobody else has labelled"
        # and "they have, on steps this mode cannot see", and those want opposite actions.
        why = (
            "one annotator"
            if len(block["annotators"]) < 2
            else "the double labels are held-out; re-run with --iaa"
        )
        lines.append(f"  inter-annotator kappa NOT COMPUTABLE -- {why}")
    else:
        for field in ("behavior", "soundness"):
            kappa = block[field]["kappa"]
            lines.append(
                f"  inter-annotator kappa · {field:9s} {kappa['value']:.3f}  "
                f"[{kappa['ci_low']:.3f}, {kappa['ci_high']:.3f}]  n={kappa['n']}  "
                f"({', '.join(block['annotators'])}, {block['source']})"
            )
    return "\n".join(lines)


def coverage(*, include_heldout: bool) -> dict[str, Any]:
    """Which labelled steps have no classifier prediction, without scoring anything.

    **M2-17's missing pre-flight.** The `--final` read happens once, and it now refuses if
    any labelled step is unmatched -- correct, but it tells you at the worst possible
    moment. This is the same question asked in advance and for free.

    `include_heldout=True` reads the held-out *step ids* to check presence. That is not the
    C5.4 read: nothing here joins a human label to a classifier label or computes any
    statistic. The held-out guard protects the labels from being **scored** against the
    classifier before the freeze, and asking "did the pipeline emit a prediction for this
    step id" touches neither the label's value nor the prediction's.

    This exists because `mb-09:thinking` -- which carries **10 of the 50 held-out steps** --
    fails intermittently with `classifier_parse_failure` (26 rows returned for 25 steps,
    surviving the repair retry), and a failed chunk nulls every label in the arm while the
    arm's `status` stays `"ok"`.
    """
    labels = load_labels(include_heldout=include_heldout)
    predictions = load_predictions()
    missing = unmatched(labels, predictions, "behavior_label", "behavior")
    by_trace: dict[str, int] = defaultdict(int)
    for row in labels:
        if row["step_id"] in set(missing):
            by_trace[f"{row.get('item_id', '?')}:{row.get('strategy', '?')}"] += 1
    return {
        "labels": len(labels),
        "unmatched": len(missing),
        "unmatched_step_ids": sorted(missing),
        "by_trace": dict(by_trace),
        "ready": not missing,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rlens-calibrate", description=__doc__)
    ap.add_argument("--final", action="store_true", help="read the held-out 50 (C5.4 guarded)")
    ap.add_argument("--dev", action="store_true", help="dev set only (the default)")
    ap.add_argument(
        "--iaa",
        action="store_true",
        help="also compute B4 #1 on the double-labelled held-out steps (human vs human only)",
    )
    ap.add_argument("--json", action="store_true", help="print the results instead of a summary")
    ap.add_argument(
        "--coverage",
        action="store_true",
        help="pre-flight: does every labelled step have a prediction? scores nothing",
    )
    ap.add_argument("--out", default=str(RESULTS_DIR / "latest.json"))
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.iaa and args.final:
        sys.stderr.write(
            "--iaa and --final together is refused. --final already reads the held-out set "
            "and scores the classifier against it; --iaa reads it for human-vs-human only. "
            "Asking for both leaves it ambiguous which read this was, and C5.4's "
            "'opened once' is a count somebody has to be able to audit afterwards.\n"
        )
        return 2

    if args.coverage:
        report = coverage(include_heldout=args.final)
        scope = "dev + held-out" if args.final else "dev"
        print(f"\ncoverage · {scope} · bundle {PROMPT_BUNDLE_VERSION}")
        print("=" * 78)
        print(f"  {report['labels']} labelled steps, {report['unmatched']} with no prediction")
        for trace, n in sorted(report["by_trace"].items()):
            print(f"    {trace:<24} {n} unmatched")
        if report["ready"]:
            print("  READY -- every labelled step carries a prediction.")
            return 0
        print(
            "  NOT READY. Re-run the corpus (`make report ARGS=--all`) and check again.\n"
            "  A chunk that fails to parse nulls every label in its arm while the arm's\n"
            "  status stays 'ok', so this is invisible in the report itself."
        )
        return 1

    if args.final:
        try:
            check_final_allowed()
        except CalibrationRefused as exc:
            sys.stderr.write(f"{exc}\n")
            return 2

    results = build_results(final=args.final, iaa_heldout=args.iaa)

    # **The published read does not get to quietly shrink its own denominator.**
    # `--final` runs once (C5.4). If a classifier call degraded that day, the labelled
    # steps it dropped would come off the bottom of the headline kappa's n and the only
    # evidence would be two fields in this file that disagree. Measured, not hypothesised:
    # a dev pass at bundle e8952d4d3c51 reported kappa over n=32 under a header line
    # reading "40 labels". On the dev path this is a loud warning, because M2-3's loop has
    # to keep working on partial data; on the final path it is a refusal.
    missing = results["run"].get("unmatched_step_ids") or []
    if args.final and missing:
        sys.stderr.write(
            f"REFUSING the --final read: {len(missing)} of {results['run']['labels_scored']} "
            "held-out labelled steps have no classifier prediction.\n"
            "The published kappa would be computed over the remainder and would report that "
            "smaller n as though it were the set.\n"
            "Re-run the corpus so every labelled step carries a prediction, then run --final "
            "again. This read has not been spent.\n"
            f"Unmatched: {', '.join(missing[:10])}"
            f"{' ...' if len(missing) > 10 else ''}\n"
        )
        return 2

    out = pathlib.Path(args.out)

    # A dev run does not READ the double labels, so it has nothing to say about them --
    # and until M3-5c's cold run it said `null` anyway, over the top of a measured result.
    #
    # The sequence is P5's own documented order: `make calibrate`, then `make calibrate
    # ARGS="--iaa"`. Run the first alone -- on a fresh checkout, or any time at all -- and
    # B4 #1's published headline (behavior kappa 0.867, soundness 0.935, n=50) became two
    # nulls under a note reading "the second annotator has not labelled yet". Ankit
    # labelled on 15 Sep and his 50 rows are committed. The file asserted something false
    # about its own evidence, FE-6 renders this file VERBATIM, and the page would have
    # gone back to "not yet measured" -- which reads as an honest empty state rather than
    # as an erasure. Exactly FE-11's finding in the other direction: understating is not
    # automatically safe, because a false statement about the evidence is still false when
    # it is modest.
    #
    # Carried forward ONLY when this run did not look. `--iaa` and `--final` do read the
    # double labels, so a null from either is a measurement and is written as one.
    if not (args.iaa or args.final) and out.exists():
        block = results["inter_annotator"]
        if block.get("behavior") is None and block.get("soundness") is None:
            try:
                prior = json.loads(out.read_text()).get("inter_annotator") or {}
            except (OSError, json.JSONDecodeError):
                prior = {}
            if prior.get("behavior") is not None or prior.get("soundness") is not None:
                # Kept verbatim and FLAGGED, never recomputed: one producer per number
                # (FE-11's rule), and a reader can see this run did not make it.
                results["inter_annotator"] = {
                    **prior,
                    "carried_forward": (
                        "Not recomputed by this run. This is a dev-mode pass, which does "
                        "not read the double-labelled steps; the block below was measured "
                        "by the last `--iaa` or `--final` run and is preserved rather than "
                        'nulled. Re-measure with `make calibrate ARGS="--iaa"`.'
                    ),
                }

    body = json.dumps(results, indent=2, sort_keys=True) + "\n"

    if args.json:
        sys.stdout.write(body)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(_render(results))
        print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
