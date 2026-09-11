"""The analysis tier's contract — `rlens.llm.analyze`. M1-9.

Separate from `test_classify.py` because the questions are different. The classifier's
tests ask *what do we do when the model answers badly*; these ask *what do we do when the
transport misbehaves*, and the answers were all bought by measurement rather than reasoned
out in advance:

* a truncation is a hard error, not a parse failure (S3),
* empty content with tokens billed is a reasoning-effort problem, not a batch-size one (S3),
* and the deadline has to be enforced from outside the call, because the one place it was
  supposed to bite is inside `urlopen` (M1-9).
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from rlens import llm


@pytest.fixture(autouse=True)
def hybrid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYZER_BACKEND", "hybrid")
    monkeypatch.setenv("MODEL_ANALYZE", "gpt-5-mini-2025-08-07")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("MOCK_LLM", raising=False)
    monkeypatch.delenv("RECORD_CASSETTES", raising=False)


def _fields(**over: Any) -> dict[str, Any]:
    base = {
        "text": '{"steps": []}',
        "model": "gpt-5-mini-2025-08-07",
        "finish_reason": "stop",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "reasoning_tokens": 5,
    }
    base.update(over)
    return base


def _stub(monkeypatch: pytest.MonkeyPatch, **over: Any) -> None:
    def fake(prompt: str, model: str, cap: int, effort: str, timeout: int) -> Any:
        return _fields(**over), {}

    monkeypatch.setattr(llm, "_analyze_hosted", fake)


# ------------------------------------------------------------------ S3's two hard errors
def test_a_bound_output_cap_raises_rather_than_returning_a_truncated_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S3 consequence 1. Retrying reproduces a truncation exactly; reporting it as
    `classifier_parse_failure` names the wrong cause and sends someone to tune a prompt."""
    _stub(monkeypatch, finish_reason="length", text='{"steps": [{"step_id": "a"')
    with pytest.raises(llm.AnalysisTruncated, match="output cap bound"):
        llm.analyze("prompt")


def test_empty_content_with_tokens_billed_points_at_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S3 failure mode 1: the model spent its whole budget in the reasoning channel. The
    lever is effort, not batch size, and the error has to say which."""
    _stub(monkeypatch, text="   ", completion_tokens=2293)
    with pytest.raises(llm.ProviderError, match="reasoning channel"):
        llm.analyze("prompt")


def test_a_truncation_is_a_subclass_of_provider_error() -> None:
    """So a caller that wants to treat every transport failure alike still can, while one
    that needs to tell them apart is able to."""
    assert issubclass(llm.AnalysisTruncated, llm.ProviderError)


# ------------------------------------------------------------------ the deadline (M1-9)
def test_the_deadline_is_enforced_from_outside_the_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**The defect this test exists for was measured, not imagined.**

    M1-9's first full pass recorded a single-chunk call taking **969 seconds against a
    110-second `ANALYSIS_DEADLINE_S`**. `urlopen(timeout=...)` bounds socket operations,
    and the block was inside the call, so the budget never applied. A deadline checked
    between reads would not have helped either — there were no reads to check between.

    Here the transport sleeps past the budget. What must happen is that the caller is
    released roughly on time, not that the socket is cleaned up.
    """
    calls = {"n": 0}

    def slow(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        time.sleep(5)
        return _fields(), {}

    monkeypatch.setattr(llm, "_analyze_hosted", slow)
    started = time.time()
    with pytest.raises(llm.ProviderError, match="TimeoutError"):
        llm.analyze("prompt", timeout=1)
    elapsed = time.time() - started

    # One retry with jitter, so the budget is spent twice plus up to 1.5s of sleep.
    assert elapsed < 5.0, f"the deadline did not release the caller ({elapsed:.1f}s)"
    assert calls["n"] == 2, "a timeout gets exactly one retry, like any transport error"


def test_an_http_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """An HTTP error is the server *answering*. Retrying a 400 re-sends the same bad
    request; the body is the only thing that says why, so it is surfaced."""
    import urllib.error

    calls = {"n": 0}

    def failing(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 400, "Bad Request", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(llm, "_analyze_hosted", failing)
    with pytest.raises(llm.ProviderError, match="HTTP 400"):
        llm.analyze("prompt")
    assert calls["n"] == 1


# ------------------------------------------------------------------ configuration
def test_an_unknown_backend_is_refused_rather_than_defaulted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo would otherwise silently select `hybrid` and publish a number attributed to
    the wrong tier. ADR-001 makes local-only a measured configuration, not a fallback."""
    monkeypatch.setenv("ANALYZER_BACKEND", "hybird")
    with pytest.raises(llm.ProviderError, match="not one of"):
        llm.analyze("prompt")


def test_hybrid_without_a_key_names_the_local_alternative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(llm.ProviderError, match="ANALYZER_BACKEND=local"):
        llm.analyze("prompt")


def test_the_request_digest_changes_with_the_prompt_and_the_model() -> None:
    """What makes a named cassette as strong as a hash-keyed one: the recorded digest
    covers the request, so a prompt edit cannot replay the old prompt's answer."""
    a = llm.request_digest("p1", backend="hybrid", model="m1")
    assert a != llm.request_digest("p2", backend="hybrid", model="m1")
    assert a != llm.request_digest("p1", backend="hybrid", model="m2")
    assert a != llm.request_digest("p1", backend="local", model="m1")
    assert a == llm.request_digest("p1", backend="hybrid", model="m1")


def test_recording_is_off_unless_asked_for(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """`.env` ships with MOCK_LLM=1 and a live key. A recorder that ran by default would
    rewrite committed cassettes on any ordinary run."""
    _stub(monkeypatch)
    monkeypatch.setattr(llm, "CASSETTE_DIR", tmp_path)
    llm.analyze("prompt", cassette="classify.test.c0")
    assert not list(tmp_path.glob("*.json"))

    monkeypatch.setenv("RECORD_CASSETTES", "1")
    llm.analyze("prompt", cassette="classify.test.c0")
    assert (tmp_path / "classify.test.c0.json").is_file()
