"""The whole pipeline, offline, from cassettes — G1 check 7 and M1-14's DoD.

Span trees in, `ReasoningReport` out, **no network**. This is the job that runs on every
PR, and it is the load-bearing half of three separate claims made elsewhere in the plan:
the frontend develops against fixtures with zero Lead dependency from W5, CI runs the real
pipeline on every PR without LLM spend, and local dev is free.

**The network is not merely unused here — it is broken on purpose.** `_no_network` replaces
the socket constructor for the duration of each test, so a code path that quietly falls
back to a live call fails loudly rather than passing slowly and billing. "We did not
observe any traffic" is not the same claim as "traffic was impossible", and only the second
one is worth putting behind a gate.
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
from typing import Any

import pytest
from rlens.llm import CASSETTE_DIR, ProviderError
from rlens.pipeline import analyze_item, validate_report
from rlens.runner.run import load_item

pytestmark = pytest.mark.integration_mock

SPANS = pathlib.Path(__file__).resolve().parent.parent.parent / "out/spans"


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a network call impossible, not merely unnecessary."""

    def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the pipeline opened a socket under MOCK_LLM=1. A cassette is missing or a "
            "code path bypasses rlens.llm -- either way this job's whole claim is that "
            "it needs no network."
        )

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setenv("MOCK_LLM", "1")
    # Replay verifies the (model, prompt) pair a cassette recorded, so it needs the pin
    # even offline -- otherwise a replayed report could name one model and carry another's
    # labels. Set here rather than assumed, so this suite runs on a bare checkout.
    monkeypatch.setenv("MODEL_ANALYZE", os.environ.get("MODEL_ANALYZE") or "gpt-5-mini-2025-08-07")
    monkeypatch.setenv("ANALYZER_BACKEND", os.environ.get("ANALYZER_BACKEND") or "hybrid")


def _items_with_spans() -> list[str]:
    if not SPANS.is_dir():
        return []
    return sorted({p.name.split(".")[0] for p in SPANS.glob("*.json")})


def _has_analysis_cassettes() -> bool:
    return any(CASSETTE_DIR.glob("classify.*.json"))


requires_cassettes = pytest.mark.skipif(
    not _items_with_spans() or not _has_analysis_cassettes(),
    reason="run `make spans` then `make record-cassettes` (M1-14)",
)


def _unreplayed(report: dict[str, Any]) -> list[str]:
    """Arms whose analysis did not come from a cassette.

    **This helper exists because the obvious version of these tests stopped asserting
    anything.** B6.5 requires a failed analysis call to degrade one arm rather than sink
    the report — so once that landed, a *missing cassette* also became a degraded arm, and
    a test that only checked "the report validates" passed with zero cassettes present and
    every arm blank. That is exactly the green-tick-over-nothing this job set has now been
    caught doing twice.

    So replay is asserted positively: no arm may carry `analysis_unavailable`.
    """
    return [
        arm["strategy"]
        for arm in report["arms"]
        if (arm.get("degraded") or {}).get("reason") == "analysis_unavailable"
    ]


@requires_cassettes
def test_the_whole_pipeline_runs_offline(offline: None) -> None:
    """**G1 check 7 and M1-14's DoD, in one assertion.**"""
    item_id = _items_with_spans()[0]
    report = analyze_item(load_item(item_id), SPANS)
    validate_report(report)
    assert report["arms"]
    assert not _unreplayed(report), "an arm fell back instead of replaying a cassette"


@requires_cassettes
def test_every_item_replays_and_validates(offline: None) -> None:
    """The whole bank, because the DoD says the full pipeline and a single item does not
    exercise the ReAct path, the 141-step chunked path or the empty-trace path."""
    failures = []
    for item_id in _items_with_spans():
        try:
            report = analyze_item(load_item(item_id), SPANS)
            validate_report(report)
            missing = _unreplayed(report)
            if missing:
                failures.append(f"{item_id}: no cassette for {missing}")
        except Exception as exc:  # the point is to collect every failure, not stop at the first
            failures.append(f"{item_id}: {type(exc).__name__}: {str(exc)[:200]}")
    assert not failures, "\n".join(failures) + "\n-> run `make record-cassettes` (M1-14)"


@requires_cassettes
def test_replay_is_byte_identical_across_runs(offline: None) -> None:
    """A replay that varies is not a replay. `generated_at` is the one field that moves,
    so it is excluded rather than the test being weakened to a shape check."""
    item = load_item(_items_with_spans()[0])
    first = analyze_item(item, SPANS)
    second = analyze_item(item, SPANS)
    for report in (first, second):
        report.pop("generated_at")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_replay_without_a_pin_explains_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """The error somebody hits running the offline suite on a bare checkout.

    Without this, `versions.analyzer_pin` raises about publishing reproducible numbers,
    which is a true sentence and the wrong explanation when what you were doing was
    running tests with no network.
    """
    from rlens.llm import analyze

    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("ANALYZER_BACKEND", "hybrid")
    monkeypatch.delenv("MODEL_ANALYZE", raising=False)
    with pytest.raises(ProviderError, match="MOCK_LLM=1 still needs MODEL_ANALYZE"):
        analyze("anything", cassette="classify.whatever.c0")


def test_a_missing_cassette_names_the_fix(offline: None) -> None:
    """The error a contributor actually hits on a fresh checkout. It must say what to run.

    A bare `FileNotFoundError` here costs somebody twenty minutes of reading the pipeline
    to discover that the answer is one make target.
    """
    from rlens.llm import analyze

    with pytest.raises(ProviderError, match="record-cassettes"):
        analyze("a prompt nobody has ever recorded", cassette="classify.nope.thinking.c0")


@requires_cassettes
def test_a_cassette_recorded_for_a_different_request_is_refused(offline: None) -> None:
    """The check that makes a *named* cassette as strong as a hash-keyed one.

    Without it, a prompt edit would replay the old prompt's answer under the new prompt's
    bundle version: a green CI run asserting behaviour that no longer exists, which is
    worse than a red one.
    """
    from rlens.llm import analyze

    name = next(CASSETTE_DIR.glob("classify.*.json")).name.removesuffix(".json")
    recorded = json.loads((CASSETTE_DIR / f"{name}.json").read_text())
    if "request_digest" not in recorded:
        pytest.skip("cassette predates the digest field")
    with pytest.raises(ProviderError, match="different request"):
        analyze("a prompt that is not the one this cassette recorded", cassette=name)


@requires_cassettes
def test_a_degraded_arm_in_replay_still_produces_a_valid_report(offline: None) -> None:
    """Whatever the recorded run did, the report conforms. If a recorded classification
    degraded, that state travels into the fixture rather than failing the job -- which is
    the behaviour FE-8 is built against."""
    for item_id in _items_with_spans():
        report = analyze_item(load_item(item_id), SPANS)
        assert not _unreplayed(report), f"{item_id}: not replayed"
        for arm in report["arms"]:
            if arm.get("degraded"):
                assert all(step["behavior"] is None for step in arm["steps"])
        validate_report(report)
