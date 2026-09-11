"""`ReasoningReport` — the G1 contract. C3.3, M1-10.

**This file is the freeze.** G1 asks one question: *is the contract stable enough for the
frontend to build against?* A schema in a directory answers that with a promise; a schema
whose three fixtures are re-validated on every PR answers it with a build failure. After
G1 a fixture that stops validating is not a test to update — it is a schema change, and a
schema change is a plan amendment (C3.3's freeze policy).

The checks below are G1 §8.2's rows 1-6, executed as code rather than read off a list.
Row 7 (cassettes replay offline) is `test_pipeline_mock.py`; rows 8-10 are a tag, a
committed file and a conversation, and none of those is a unit test's business.
"""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any

import jsonschema
import pytest
from rlens.pipeline import SCHEMA_PATH, load_schema, validate_report

pytestmark = pytest.mark.contract

FIXTURES = pathlib.Path(__file__).parent / "fixtures/reports"
#: `report_measured` is the fourth fixture and the plan named three. It is a REAL report
#: from a real run, committed alongside the three authored ones because ADR-009 found that
#: a harvested report cannot cover all five behavior classes -- the model produces one or
#: two of them on this corpus. Keeping both means the frontend gets realistic text lengths
#: and shapes from the measured one and full class coverage from the authored one, and
#: nobody has to guess which is which.
NAMES = ("report_nominal", "report_flagged", "report_degraded", "report_measured")

BEHAVIOR_CLASSES = {
    "verification",
    "backtracking",
    "subgoal_setting",
    "backward_chaining",
    "linear",
}


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text())
    return data


def steps_of(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for arm in report["arms"] for step in arm["steps"]]


# ------------------------------------------------------------------ G1 checks 1 and 2
def test_the_schema_is_itself_a_valid_json_schema() -> None:
    """A malformed schema validates everything, silently. Check the checker first."""
    schema = load_schema()
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_validates(name: str) -> None:
    """**G1 check 2, and the assertion that IS the freeze mechanism.**"""
    validate_report(load(name))


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_declares_schema_version_one(name: str) -> None:
    assert load(name)["schema_version"] == "1.0"


# ------------------------------------------------------------------ G1 check 3
def test_the_nominal_fixture_covers_all_five_behavior_classes() -> None:
    """G1 check 3. Eight frontend surfaces render a per-class legend, a distribution bar
    and a per-class filter; a class absent from every fixture is a class the frontend
    owner discovers in Month 3, in the month with no slack for discoveries."""
    labels = {
        step["behavior"]["label"] for step in steps_of(load("report_nominal")) if step["behavior"]
    }
    missing = BEHAVIOR_CLASSES - labels
    assert not missing, f"no fixture step carries {sorted(missing)}"


def test_the_nominal_pattern_profile_names_every_class_even_at_zero() -> None:
    """An absent CLASS and an absent PROFILE say different things; only the second means
    "not measured". A five-bar chart must not silently become a three-bar chart."""
    for arm in load("report_nominal")["arms"]:
        profile = (arm.get("metrics") or {}).get("pattern_profile")
        if profile is not None:
            assert set(profile) == BEHAVIOR_CLASSES


# ------------------------------------------------------------------ G1 check 4
def test_a_fully_flagged_step_exists() -> None:
    """G1 check 4 — and all four parts of it, because FE-4's side panel renders all four.

    A fixture with an `unsound` verdict and a null `error_type` would let the panel be
    built without an error-type row and the omission would surface against real data.
    """
    flagged = [
        step
        for step in steps_of(load("report_flagged"))
        if step["validity"] and step["validity"]["verdict"] == "unsound"
    ]
    assert flagged, "no unsound step"
    complete = [
        step
        for step in flagged
        if step["validity"]["error_type"]
        and step["validity"]["escalated"]
        and step["validity"]["rationale"]
    ]
    assert complete, "an unsound step exists but none carries error_type + escalated + rationale"


def test_the_flagged_fixture_has_a_contradicting_consistency_verdict_with_citations() -> None:
    """A `contradicts` verdict citing nothing is an accusation with no evidence."""
    verdicts = [
        arm["consistency"] for arm in load("report_flagged")["arms"] if arm.get("consistency")
    ]
    contradicting = [c for c in verdicts if c["verdict"] == "contradicts"]
    assert contradicting, "no contradicts verdict"
    assert all(c["cited_step_ids"] for c in contradicting)


# ------------------------------------------------------------------ G1 check 5
def test_the_degraded_fixture_reaches_every_state_fe8_must_render() -> None:
    """G1 check 5. **The highest-value fixture and the easiest to under-scope.**

    FE-8 is 1.5 h of unbudgeted Month-3 frontend work whose every state must be reachable
    in mock mode. Each state missing here becomes a Month-3 conversation with the Lead.
    """
    arms = load("report_degraded")["arms"]
    assert any(arm["status"] == "failed" for arm in arms), "no failed arm"
    assert any(
        (arm.get("degraded") or {}).get("reason") == "classifier_parse_failure" for arm in arms
    ), "no classifier_parse_failure"
    assert any(arm["trace_quality"] == "provider_summarised" for arm in arms)
    assert any(arm["escalation_capped"] for arm in arms)
    assert any(arm["budget_bound"] for arm in arms)


def test_a_degraded_arm_renders_its_steps_unannotated_rather_than_labelled() -> None:
    """C4.3's rule, visible in the artifact the frontend reads.

    The text is real and the labels are absent. A fabricated `linear` would render
    identically to a real one, which is exactly why it is forbidden.
    """
    degraded = [arm for arm in load("report_degraded")["arms"] if arm.get("degraded")]
    assert degraded
    for arm in degraded:
        assert arm["steps"], "a degraded arm still shows its steps"
        assert all(step["behavior"] is None for step in arm["steps"])
        assert all(step["validity"] is None for step in arm["steps"])


def test_a_failed_arm_is_present_rather_than_omitted() -> None:
    """An absent arm is indistinguishable from an arm nobody ran (B6.5)."""
    failed = [arm for arm in load("report_degraded")["arms"] if arm["status"] == "failed"]
    assert failed and all(arm["steps"] == [] for arm in failed)


# ------------------------------------------------------------------ G1 check 6
@pytest.mark.parametrize(
    "pointer",
    [
        ("$defs", "arm", "properties", "consistency"),
        ("$defs", "metrics", "properties", "soundness_score"),
        ("$defs", "validity", "properties", "escalated"),
        ("$defs", "arm", "properties", "escalation_capped"),
        ("$defs", "arm", "properties", "budget_bound"),
        ("$defs", "versions", "properties", "judge_triage_pin"),
        ("$defs", "versions", "properties", "judge_escalate_pin"),
        ("$defs", "measurement_context", "properties", "classifier_kappa_heldout"),
        ("$defs", "measurement_context", "properties", "majority_class_baseline"),
    ],
)
def test_the_schema_accommodates_fields_month_1_cannot_produce(pointer: tuple[str, ...]) -> None:
    """G1 check 6. Every one of these is written by M2 or M3 and must not require a
    schema change then — after G1 a breaking change is a plan amendment."""
    node: Any = load_schema()
    for key in pointer:
        assert key in node, f"{'.'.join(pointer)} is missing from the schema"
        node = node[key]


def test_month_two_fields_are_nullable_so_month_one_can_emit_an_honest_null() -> None:
    """I3: a `measurement_context` of zeros renders as "kappa 0.0" — a measured failure —
    where the truth is "not measured yet". Nullability is what keeps those apart."""
    props = load_schema()["$defs"]["measurement_context"]["properties"]
    for name, spec in props.items():
        assert "null" in spec["type"], f"measurement_context.{name} cannot be null"


# ------------------------------------------------------------------ the freeze's teeth
def test_an_unknown_field_is_rejected() -> None:
    """`additionalProperties: false` is what makes the freeze mechanical.

    Without it a new field could be added anywhere without touching the schema, and G1
    would be freezing a document that permits everything.
    """
    report = load("report_flagged")
    report["surprise"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_an_unknown_field_inside_an_arm_is_rejected() -> None:
    report = copy.deepcopy(load("report_flagged"))
    report["arms"][0]["surprise"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_a_behavior_label_outside_the_taxonomy_is_rejected() -> None:
    report = copy.deepcopy(load("report_flagged"))
    report["arms"][0]["steps"][0]["behavior"]["label"] = "reflection"
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_a_contradicts_verdict_citing_nothing_is_rejected() -> None:
    """The schema enforces A.3's rule rather than trusting the judge to follow it."""
    report = copy.deepcopy(load("report_flagged"))
    for arm in report["arms"]:
        if arm.get("consistency") and arm["consistency"]["verdict"] == "contradicts":
            arm["consistency"]["cited_step_ids"] = []
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_a_malformed_step_id_is_rejected() -> None:
    """`step_id` is the join key for every label ever written (C3.2, Hazard 1)."""
    report = copy.deepcopy(load("report_flagged"))
    report["arms"][0]["steps"][0]["step_id"] = "thinking-fx01d-0"
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_a_confidence_outside_zero_to_one_is_rejected() -> None:
    report = copy.deepcopy(load("report_flagged"))
    report["arms"][0]["steps"][0]["behavior"]["confidence"] = 1.2
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_a_bumped_schema_version_is_rejected_until_the_schema_is_bumped_with_it() -> None:
    """C3.3's freeze policy: a breaking change bumps `schema_version`, regenerates the
    fixtures and notifies the frontend owner *in the same PR*. The `const` is what makes
    a half-done version bump fail rather than pass quietly."""
    report = copy.deepcopy(load("report_flagged"))
    report["schema_version"] = "1.1"
    with pytest.raises(jsonschema.ValidationError):
        validate_report(report)


def test_the_measured_fixture_is_actually_measured() -> None:
    """It is the only fixture whose provenance is a run, so it is the only one that can
    go stale. A `fixture000000000` pin here would mean somebody hand-edited it, which
    would quietly turn the repo's one piece of real report data into more authored data."""
    report = load("report_measured")
    assert report["versions"]["model_pin"] != "fixture000000000"
    assert report["item"]["id"].startswith("mb-")
    assert report["versions"]["judge_triage_pin"]


def test_the_authored_fixtures_say_so_in_the_pin() -> None:
    """The inverse guard: an authored fixture must not be mistakable for measured data."""
    for name in ("report_nominal", "report_flagged", "report_degraded"):
        assert load(name)["versions"]["model_pin"] == "fixture000000000"
        assert load(name)["item"]["id"].startswith("fx-")


def test_the_schema_ships_inside_the_package() -> None:
    """I1: the analyzer is a standalone pip package. A schema living in `tests/` would
    validate in CI and be absent from the wheel the backend imports."""
    assert SCHEMA_PATH.is_file()
    assert "src/rlens/schemas" in SCHEMA_PATH.as_posix()


# ------------------------------------------------------------------ G1 check 10
def test_every_frontend_surface_is_annotated_with_the_fixture_it_consumes() -> None:
    """**G1 check 10, as amendment 001 redefined it.**

    The original check was a 15-minute walkthrough with the frontend owner. There is no
    frontend owner — Amit is the sole contributor and cannot walk himself through the
    fixtures — so the amendment replaced the conversation with a written artifact: each
    fixture annotated with which UI surface consumes it.

    A written artifact that nothing checks decays into a written artifact that is wrong,
    which is worse than the conversation it replaced. So the table is asserted: all eight
    surfaces named, and every fixture the table cites actually present.
    """
    readme = (FIXTURES / "README.md").read_text()
    for surface in (f"FE-{n}" for n in range(1, 9)):
        assert f"**{surface}**" in readme, f"{surface} has no row in the fixtures README"
    for name in NAMES:
        assert f"`{name}`" in readme, f"{name} is committed but no surface claims it"


# ------------------------------------------------------------------ B6.5, at the pipeline
def test_an_analysis_failure_degrades_one_arm_and_spares_the_others(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """**B6.5 as an assertion rather than an intention.**

    `classify` returns a degraded result when the *model* answers badly, and raises when
    the *transport* fails — a truncation, a deadline, a dead connection. Letting that raise
    propagate would lose two good arms to one bad call, which is exactly backwards from
    what C4.1's failed-arm state exists for.

    The arm has to be **present** and marked failed. An absent arm is indistinguishable
    from one nobody ran.
    """
    import json as _json

    from rlens import pipeline
    from rlens.llm import ProviderError

    spans = pathlib.Path(__file__).resolve().parents[2] / "out/spans"
    if not spans.is_dir() or not list(spans.glob("mb-13.*.json")):
        pytest.skip("no span trees; run `make spans`")

    calls = {"n": 0}

    def sometimes_fails(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 2:  # the thinking arm
            raise ProviderError("the 16000-token output cap bound")
        from rlens.classify import ClassificationResult

        return ClassificationResult(strategy="x", item_id="mb-13")

    monkeypatch.setattr(pipeline, "classify", sometimes_fails)
    item = _json.loads(
        (pathlib.Path(__file__).resolve().parents[2] / "problem-bank/items/mb-13.json").read_text()
    )
    report = pipeline.analyze_item(item, spans)

    validate_report(report)
    assert len(report["arms"]) == 3, "the arm must be present, not omitted"
    broken = [arm for arm in report["arms"] if arm.get("degraded")]
    assert len(broken) == 1
    assert broken[0]["degraded"]["reason"] == "analysis_unavailable"

    # **`status` stays `ok`, and that is the half of this test that matters.** The arm
    # generated fine — there is a complete trace. `failed` means the generation call did
    # not return, and claiming it here would tell a reader the model never answered. That
    # is the `unparsed`-vs-`wrong` distinction M1-5 and M1-8 each paid for, arriving a
    # third time in a third place.
    assert broken[0]["status"] == "ok"
    assert broken[0]["steps"], "the steps survive — the trace was never the problem"
    assert all(step["behavior"] is None for step in broken[0]["steps"])
    assert all(arm["status"] != "failed" for arm in report["arms"])
