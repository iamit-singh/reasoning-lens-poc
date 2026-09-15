"""`make calibrate` — the guards and the shape. C5.4, C5.5, M2-13.

Two thirds of this file is about **refusing**, and that is the right proportion. The
happy path is a join and some arithmetic that `test_metrics.py` already checks against
sklearn. What M2-13 actually buys is that the held-out set cannot be read casually and
that a partial label file does not take the tool down during the only weeks anybody needs
it.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from rlens import calibrate as C


def _label(step_id: str, behavior: str, annotator: str = "amit", **over: Any) -> dict[str, Any]:
    row = {
        "step_id": step_id,
        "item_id": "mb-01",
        "strategy": "thinking",
        "text": "some step",
        "behavior_label": behavior,
        "soundness_label": "sound",
        "annotator": annotator,
        "labeled_at": "2026-10-08T10:00:00Z",
        "rubric_version": "v1",
    }
    row.update(over)
    return row


def _report(step_ids: list[str], behaviors: list[str]) -> dict[str, Any]:
    return {
        "item": {"id": "mb-01"},
        "arms": [
            {
                "strategy": "thinking",
                "steps": [
                    {
                        "step_id": sid,
                        "behavior": {"label": b, "confidence": 0.8},
                        "validity": {"verdict": "sound", "confidence": 0.9, "escalated": False},
                    }
                    for sid, b in zip(step_ids, behaviors, strict=True)
                ],
            }
        ],
    }


@pytest.fixture
def workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path):
    """Point the module at a scratch tree. Nothing here touches the real label files."""
    labels = tmp_path / "labels"
    reports = tmp_path / "reports"
    labels.mkdir()
    reports.mkdir()
    monkeypatch.setattr(C, "LABELS_DIR", labels)
    monkeypatch.setattr(C, "REPORTS_DIR", reports)
    monkeypatch.setattr(C, "FREEZE_FILE", labels / "HELDOUT_FREEZE")
    monkeypatch.setattr(C, "HELDOUT_FILE", labels / "heldout-50.jsonl")
    # Absent unless a test writes it. `heldout_step_ids()` degrades to the filename rule
    # when there is no draw, and every test written before the draw-keyed guard relies on
    # that: their step ids are not in any draw.
    monkeypatch.setattr(C, "SAMPLING_FILE", tmp_path / "sampling.json")
    return labels, reports


# ------------------------------------------------------------------ C5.4's guards
def test_final_refuses_when_the_heldout_file_does_not_exist(workspace) -> None:
    with pytest.raises(C.CalibrationRefused, match="does not exist yet"):
        C.check_final_allowed()


def test_final_refuses_when_the_prompt_bundle_is_not_frozen(workspace) -> None:
    """**The guard C5.4 is actually for.** Scoring the held-out set against an unfrozen
    bundle means the number can be re-rolled until it is liked — which is the one thing
    the held-out set exists to prevent."""
    labels, _ = workspace
    (labels / "heldout-50.jsonl").write_text("")
    with pytest.raises(C.CalibrationRefused, match="not frozen"):
        C.check_final_allowed()


def test_final_refuses_when_the_prompts_changed_after_the_freeze(workspace) -> None:
    """A freeze that does not check *what* was frozen is a file, not a freeze."""
    labels, _ = workspace
    (labels / "heldout-50.jsonl").write_text("")
    (labels / "HELDOUT_FREEZE").write_text("bundle=deadbeefcafe sha=abc123\n")
    with pytest.raises(C.CalibrationRefused, match="prompts have changed"):
        C.check_final_allowed()


def test_final_is_allowed_once_the_freeze_names_the_current_bundle(workspace) -> None:
    from rlens.versions import PROMPT_BUNDLE_VERSION

    labels, _ = workspace
    (labels / "heldout-50.jsonl").write_text("")
    (labels / "HELDOUT_FREEZE").write_text(f"bundle={PROMPT_BUNDLE_VERSION}\n")
    C.check_final_allowed()  # must not raise


def test_the_heldout_file_is_not_read_without_final(workspace) -> None:
    """The default invocation must not touch it. "Opened once" has to be enforced, not
    promised — a tool that reads it by default makes the promise somebody's discipline."""
    labels, _ = workspace
    (labels / "heldout-50.jsonl").write_text(json.dumps(_label("thinking:a:0", "linear")) + "\n")
    (labels / "amit.jsonl").write_text(json.dumps(_label("thinking:a:1", "linear")) + "\n")

    assert len(C.load_labels(include_heldout=False)) == 1
    assert len(C.load_labels(include_heldout=True)) == 2


def _draw(*step_ids: str) -> None:
    """A random-90-shaped draw whose split point is `C.HELDOUT_SPLIT_AT`."""
    C.SAMPLING_FILE.write_text(json.dumps({"draw": {"ordered_step_ids": list(step_ids)}}))


def test_a_heldout_step_is_excluded_from_dev_whatever_file_it_arrived_in(workspace) -> None:
    """**The guard is keyed on the draw, not the filename.**

    The labelling tool appends to a file named after the *annotator*, and a pass that ran
    past position 40 put 50 held-out rows in `amit.jsonl` — where the default
    `make calibrate` scored them as dev. Tuning a prompt against that number is tuning
    against the held-out set, which is the one thing C5.4 exists to prevent.
    """
    labels, _ = workspace
    dev_ids = [f"thinking:a:{i}" for i in range(C.HELDOUT_SPLIT_AT)]
    held_ids = ["thinking:a:90", "thinking:a:91"]
    _draw(*dev_ids, *held_ids)

    # Exactly the shape the real pass produced: both halves in one annotator-named file.
    (labels / "amit.jsonl").write_text(
        "".join(json.dumps(_label(sid, "linear")) + "\n" for sid in dev_ids + held_ids)
    )

    dev = C.load_labels(include_heldout=False)
    assert {row["step_id"] for row in dev} == set(dev_ids)
    assert len(C.load_labels(include_heldout=True)) == len(dev_ids) + len(held_ids)


def test_the_second_annotators_file_does_not_leak_the_heldout_set(workspace) -> None:
    """W6's shape. `annotator-2.md` tells Ankit his labels go in `labels/<annotator>.jsonl`
    and he labels *nothing but* the held-out 50, so a filename-keyed guard would have let
    his entire pass into the dev number."""
    labels, _ = workspace
    _draw(*[f"thinking:a:{i}" for i in range(C.HELDOUT_SPLIT_AT)], "thinking:a:90")

    (labels / "ankit.jsonl").write_text(
        json.dumps(_label("thinking:a:90", "linear", "ankit")) + "\n"
    )

    assert C.load_labels(include_heldout=False) == []
    assert len(C.load_labels(include_heldout=True)) == 1


# ------------------------------------------------------------------ running on partial data
def test_it_runs_with_no_labels_at_all(workspace) -> None:
    """**M2-13's DoD.** In W5 there are 40 of 100 dev labels; a tool that refused until the
    set was complete would be unavailable for the weeks it exists to serve."""
    results = C.build_results(final=False)
    assert results["run"]["labels_loaded"] == 0
    assert results["classifier_vs_human"]["behavior"] is None
    assert results["inter_annotator"]["behavior"] is None
    assert results["measurement_context"]["classifier_kappa_dev"] is None


def test_it_runs_with_labels_that_have_no_matching_prediction(workspace) -> None:
    labels, _ = workspace
    (labels / "amit.jsonl").write_text(
        json.dumps(_label("thinking:nobody-predicted-this:0", "linear")) + "\n"
    )
    results = C.build_results(final=False)
    assert results["run"]["labels_loaded"] == 1
    assert results["run"]["steps_joined_behavior"] == 0
    assert results["classifier_vs_human"]["behavior"] is None


# ------------------------------------------------------------------ the join
def test_labels_join_to_predictions_on_step_id(workspace) -> None:
    labels, reports = workspace
    ids = [f"thinking:x:{i}" for i in range(6)]
    human = ["linear", "linear", "verification", "linear", "subgoal_setting", "linear"]
    machine = ["linear", "verification", "verification", "linear", "subgoal_setting", "linear"]
    (labels / "amit.jsonl").write_text(
        "\n".join(json.dumps(_label(sid, b)) for sid, b in zip(ids, human, strict=True)) + "\n"
    )
    (reports / "mb-01.report.json").write_text(json.dumps(_report(ids, machine)))

    results = C.build_results(final=False)
    block = results["classifier_vs_human"]["behavior"]
    assert block["n"] == 6
    assert block["raw_agreement"]["value"] == pytest.approx(5 / 6)
    # And the baseline travels with it, per ADR-010.
    assert block["majority_class_baseline"]["value"] == pytest.approx(4 / 6)


def test_a_relabelled_step_takes_the_later_label(workspace) -> None:
    """`label.py` appends and never rewrites, so re-labelling produces two rows. Taking the
    first would score an annotator against a judgement they had already corrected."""
    labels, _ = workspace
    rows = [
        _label("thinking:x:0", "linear", labeled_at="2026-10-08T10:00:00Z"),
        _label("thinking:x:0", "verification", labeled_at="2026-10-08T11:00:00Z"),
    ]
    (labels / "amit.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    loaded = C.load_labels(include_heldout=False)
    assert len(loaded) == 1 and loaded[0]["behavior_label"] == "verification"


def test_a_skipped_label_is_counted_and_not_scored(workspace) -> None:
    """A skip says the rubric could not decide the step. Scoring it as a disagreement would
    turn an admission of ambiguity into evidence of error."""
    labels, reports = workspace
    (labels / "amit.jsonl").write_text(
        json.dumps(_label("thinking:x:0", "linear"))
        + "\n"
        + json.dumps(_label("thinking:x:1", None, skipped=True, soundness_label=None))
        + "\n"
    )
    (reports / "mb-01.report.json").write_text(
        json.dumps(_report(["thinking:x:0", "thinking:x:1"], ["linear", "linear"]))
    )
    results = C.build_results(final=False)
    assert results["run"]["labels_skipped_by_annotator"] == 1
    assert results["classifier_vs_human"]["behavior"]["n"] == 1


# ------------------------------------------------------------------ B4 #1
def test_inter_annotator_kappa_needs_two_annotators(workspace) -> None:
    """**Not harder with one annotator. Not computable.** A null must not read as a zero,
    because a zero says two people disagreed and nobody disagreed with anybody."""
    labels, _ = workspace
    (labels / "amit.jsonl").write_text(
        "\n".join(json.dumps(_label(f"thinking:x:{i}", "linear")) for i in range(10)) + "\n"
    )
    assert C.build_results(final=False)["inter_annotator"]["behavior"] is None


def test_inter_annotator_kappa_is_computed_once_two_people_overlap(workspace) -> None:
    labels, _ = workspace
    ids = [f"thinking:x:{i}" for i in range(8)]
    a = ["linear", "linear", "verification", "linear", "verification", "linear", "linear", "linear"]
    b = [
        "linear",
        "verification",
        "verification",
        "linear",
        "verification",
        "linear",
        "linear",
        "linear",
    ]
    (labels / "amit.jsonl").write_text(
        "\n".join(json.dumps(_label(s, v, "amit")) for s, v in zip(ids, a, strict=True)) + "\n"
    )
    (labels / "ankit.jsonl").write_text(
        "\n".join(json.dumps(_label(s, v, "ankit")) for s, v in zip(ids, b, strict=True)) + "\n"
    )
    block = C.build_results(final=False)["inter_annotator"]["behavior"]
    assert block is not None and block["n"] == 8
    assert block["raw_agreement"]["value"] == pytest.approx(7 / 8)


# ------------------------------------------------------------------ the published shape
def test_the_output_carries_provenance_and_nulls_rather_than_zeros(workspace) -> None:
    """FE-6 renders this verbatim with zero hard-coded numbers, so what is absent here is
    absent from the page. I3: a null must render as "not yet measured", never as 0."""
    results = C.build_results(final=False)
    run = results["run"]
    assert run["prompt_bundle_version"] and run["analyzer_version"]
    assert run["mode"] == "dev"

    context = results["measurement_context"]
    for key in (
        "classifier_kappa_heldout",
        "classifier_kappa_dev",
        "majority_class_baseline",
        "per_class_f1",
        "judge_precision",
        "judge_recall",
        "consistency_fp_rate",
    ):
        assert key in context, f"{key} is missing from measurement_context"
        assert context[key] is None or isinstance(context[key], dict)


def test_a_dev_run_never_populates_the_heldout_kappa(workspace) -> None:
    """The two numbers are not interchangeable, and a page that showed a dev κ under a
    held-out label would be the single most misleading thing this project could publish."""
    labels, reports = workspace
    ids = [f"thinking:x:{i}" for i in range(4)]
    (labels / "amit.jsonl").write_text(
        "\n".join(json.dumps(_label(s, "linear")) for s in ids) + "\n"
    )
    (reports / "mb-01.report.json").write_text(json.dumps(_report(ids, ["linear"] * 4)))
    results = C.build_results(final=False)
    assert results["measurement_context"]["classifier_kappa_heldout"] is None
    assert results["measurement_context"]["classifier_kappa_dev"] is not None
    assert results["measurement_context"]["n_heldout"] is None


# ------------------------------------------------- B4 #1 lives on the HELD-OUT 50 (M2-2)
def _double_labelled_heldout(labels: pathlib.Path) -> list[str]:
    """W6's real shape: 40 dev steps, and 4 held-out steps that BOTH annotators labelled.

    This is not a contrived arrangement. `annotator-2.md` sends the second annotator to the
    held-out 50 and to nothing else, so every step B4 #1 is computed from is a step C5.4
    excludes from the default run.
    """
    dev_ids = [f"thinking:a:{i}" for i in range(C.HELDOUT_SPLIT_AT)]
    held_ids = [f"thinking:a:{90 + i}" for i in range(4)]
    _draw(*dev_ids, *held_ids)
    (labels / "amit.jsonl").write_text(
        "".join(json.dumps(_label(sid, "linear")) + "\n" for sid in dev_ids)
    )
    (labels / "heldout-50.jsonl").write_text(
        "".join(json.dumps(_label(sid, "linear", "amit")) + "\n" for sid in held_ids)
        + "".join(
            json.dumps(_label(sid, b, "ankit")) + "\n"
            for sid, b in zip(held_ids, ["linear", "linear", "verification", "linear"], strict=True)
        )
    )
    return held_ids


def test_the_default_run_cannot_compute_the_agreement_it_is_told_to_compute(workspace) -> None:
    """**The defect M2-2 exposed.** `annotator-2.md` says: *"make calibrate — IAA on the 50
    double-labelled steps"*. It does not, and it never could: the C5.4 exclusion drops every
    held-out step, both passes sit entirely inside the held-out 50, and the run reports
    NOT COMPUTABLE with 100 labels from two people on disk.

    A null that means "not measured yet" is honest. A null that means "measured, then
    discarded by a guard aimed at something else" is a number going missing.
    """
    labels, _ = workspace
    _double_labelled_heldout(labels)
    assert C.build_results(final=False)["inter_annotator"]["behavior"] is None


def test_iaa_computes_the_heldout_agreement_and_does_not_need_the_freeze(workspace) -> None:
    """B4 #1 is human-vs-human and touches no classifier output, so it is not the C5.4 read
    and must not wait on M2-16's freeze. The ordering control requires the opposite: the IAA
    κ has to be computable, and committed, *before* anything scores the classifier."""
    labels, _ = workspace
    _double_labelled_heldout(labels)

    results = C.build_results(final=False, iaa_heldout=True)
    block = results["inter_annotator"]["behavior"]
    assert block is not None, "the double labels are on disk; B4 #1 is computable"
    assert block["n"] == 4
    assert results["inter_annotator"]["soundness"] is not None
    assert results["inter_annotator"]["annotators"] == ["amit", "ankit"]
    assert results["run"]["mode"] == "dev+iaa"


def test_iaa_never_scores_the_classifier_against_a_heldout_step(workspace) -> None:
    """**The whole risk of this mode in one test.**

    `--iaa` widens the label set human-vs-human reads. If that same widened set reached the
    classifier join, the held-out 50 would be scored against the classifier in a run that
    needs no freeze and takes no deliberate act — which is precisely what C5.4 forbids and
    exactly how the filename-keyed guard failed before it.
    """
    labels, reports = workspace
    held_ids = _double_labelled_heldout(labels)
    dev_ids = [f"thinking:a:{i}" for i in range(C.HELDOUT_SPLIT_AT)]
    # Predictions exist for BOTH halves, so a leak would show up as a bigger n.
    (reports / "mb-01.report.json").write_text(
        json.dumps(_report(dev_ids + held_ids, ["linear"] * len(dev_ids) + ["verification"] * 4))
    )

    dev = C.build_results(final=False)
    iaa = C.build_results(final=False, iaa_heldout=True)

    assert iaa["classifier_vs_human"] == dev["classifier_vs_human"]
    assert iaa["classifier_vs_human"]["behavior"]["n"] == C.HELDOUT_SPLIT_AT
    assert iaa["measurement_context"]["classifier_kappa_heldout"] is None
    assert iaa["measurement_context"]["n_heldout"] is None
    assert iaa["run"]["labels_scored"] == C.HELDOUT_SPLIT_AT


def test_the_iaa_flag_is_refused_together_with_final(workspace) -> None:
    """`--final` already reads the held-out set; asking for both says the caller has not
    decided which read this is. C5.4's "opened once" is a count, and an ambiguous invocation
    is how a count becomes an argument later."""
    assert C.main(["--iaa", "--final", "--json"]) == 2
