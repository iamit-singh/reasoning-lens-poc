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
