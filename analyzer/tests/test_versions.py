"""Unit tests for the C2.3 version/cache-key discipline. Deterministic, no LLM."""

from __future__ import annotations

import pytest
from rlens import versions

PIN = "test-model-2026-09-01"


def test_prompt_bundle_version_is_a_content_hash() -> None:
    assert versions.PROMPT_BUNDLE_VERSION
    assert versions._compute_prompt_bundle_version() == versions.PROMPT_BUNDLE_VERSION


def test_cache_key_is_deterministic() -> None:
    a = versions.cache_key("item-01", "cot", pin=PIN)
    b = versions.cache_key("item-01", "cot", pin=PIN)
    assert a == b
    assert len(a) == 64


@pytest.mark.parametrize(
    ("item_id", "strategy", "pin"),
    [
        ("item-02", "cot", PIN),
        ("item-01", "thinking", PIN),
        ("item-01", "cot", "test-model-2026-10-01"),
    ],
)
def test_cache_key_varies_with_every_input(item_id: str, strategy: str, pin: str) -> None:
    baseline = versions.cache_key("item-01", "cot", pin=PIN)
    assert versions.cache_key(item_id, strategy, pin=pin) != baseline


def test_cache_key_varies_with_the_three_code_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    baseline = versions.cache_key("item-01", "cot", pin=PIN)
    for attr in ("RUNNER_VERSION", "ANALYZER_VERSION", "PROMPT_BUNDLE_VERSION"):
        monkeypatch.setattr(versions, attr, "bumped")
        assert versions.cache_key("item-01", "cot", pin=PIN) != baseline
        monkeypatch.undo()


def test_model_pin_refuses_to_be_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_PIN", raising=False)
    with pytest.raises(RuntimeError, match="MODEL_PIN is unset"):
        versions.model_pin()


def test_model_pin_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PIN", PIN)
    assert versions.model_pin() == PIN
