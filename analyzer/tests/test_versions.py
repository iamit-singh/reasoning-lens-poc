"""Unit tests for the version / cache-key discipline. Deterministic, no LLM.

Amended alongside ADR-001: the generation pin is a tuple, and the analyzer pin is
separate because generation (local) and analysis (OpenAI) move independently.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rlens import versions
from rlens.versions import GenerationPin

ANALYZE = "test-analyzer-2026-09-01"

PIN = GenerationPin(
    model="gpt-oss:20b",
    digest="sha256:abc123",
    quantization="mxfp4",
    runtime="ollama 0.12.0",
    temperature=0.0,
    top_p=1.0,
    seed=20260910,
    reasoning_effort="medium",
)


def test_prompt_bundle_version_is_a_content_hash() -> None:
    assert versions.PROMPT_BUNDLE_VERSION
    assert versions._compute_prompt_bundle_version() == versions.PROMPT_BUNDLE_VERSION


def test_cache_key_is_deterministic() -> None:
    a = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    b = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    assert a == b
    assert len(a) == 64


@pytest.mark.parametrize(
    ("item_id", "strategy", "analyze"),
    [
        ("item-02", "cot", ANALYZE),
        ("item-01", "thinking", ANALYZE),
        ("item-01", "cot", "test-analyzer-2026-10-01"),
    ],
)
def test_cache_key_varies_with_every_scalar_input(
    item_id: str, strategy: str, analyze: str
) -> None:
    baseline = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    assert versions.cache_key(item_id, strategy, gen=PIN, analyze=analyze) != baseline


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "qwen3:14b"),
        ("digest", "sha256:def456"),
        ("quantization", "q4_k_m"),
        ("runtime", "ollama 0.13.0"),
        ("temperature", 0.7),
        ("top_p", 0.9),
        ("seed", 1),
        ("reasoning_effort", "high"),
    ],
)
def test_every_generation_pin_field_changes_the_cache_key(field: str, value: object) -> None:
    """The whole point of the tuple pin: an id alone does not reproduce a local number.

    Re-pulling a tag can yield different weights, and sampling settings change the
    output, so each field must invalidate the cache on its own.
    """
    baseline = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    mutated = GenerationPin(**{**PIN.__dict__, field: value})
    assert versions.cache_key("item-01", "cot", gen=mutated, analyze=ANALYZE) != baseline


def test_cache_key_varies_with_the_backend_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    """hybrid and local-only must not share cache entries -- they are different analyzers,
    and both configurations are measured and reported side by side (ADR-001)."""
    monkeypatch.setenv("ANALYZER_BACKEND", "hybrid")
    hybrid = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    monkeypatch.setenv("ANALYZER_BACKEND", "local")
    assert versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE) != hybrid


def test_cache_key_varies_with_the_code_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    baseline = versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE)
    for attr in ("RUNNER_VERSION", "ANALYZER_VERSION", "PROMPT_BUNDLE_VERSION"):
        monkeypatch.setattr(versions, attr, "bumped")
        assert versions.cache_key("item-01", "cot", gen=PIN, analyze=ANALYZE) != baseline
        monkeypatch.undo()


def test_analyzer_pin_refuses_to_be_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_ANALYZE", raising=False)
    with pytest.raises(RuntimeError, match="MODEL_ANALYZE is unset"):
        versions.analyzer_pin()


@pytest.mark.parametrize("alias", ["gpt-5-latest", "some-model-preview", "some-model-turbo"])
def test_analyzer_pin_refuses_a_floating_alias(monkeypatch: pytest.MonkeyPatch, alias: str) -> None:
    """A number pinned to an alias expires silently."""
    monkeypatch.setenv("MODEL_ANALYZE", alias)
    with pytest.raises(RuntimeError, match="floating alias"):
        versions.analyzer_pin()


def test_analyzer_pin_accepts_a_dated_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_ANALYZE", ANALYZE)
    assert versions.analyzer_pin() == ANALYZE


def test_an_unpinned_generation_model_is_detectable() -> None:
    """A report built on an empty pin is not reproducible, so the gap must be visible
    rather than silently defaulting."""
    assert PIN.unpinned_fields() == ()
    fresh = GenerationPin("", "", "", "", 0.0, 1.0, 0, "")
    assert set(fresh.unpinned_fields()) == {"model", "digest", "quantization", "runtime"}


def test_generation_pin_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_MODEL", "gpt-oss:20b")
    monkeypatch.setenv("LOCAL_MODEL_DIGEST", "sha256:abc123")
    monkeypatch.setenv("LOCAL_QUANTIZATION", "mxfp4")
    monkeypatch.setenv("LOCAL_RUNTIME", "ollama 0.12.0")
    monkeypatch.setenv("GEN_SEED", "20260910")
    monkeypatch.setenv("LOCAL_REASONING_EFFORT", "medium")
    assert versions.generation_pin().fingerprint() == PIN.fingerprint()


def test_changelog_is_not_hashed_into_the_bundle_version(tmp_path: Path) -> None:
    """M2-3's changelog lives in `prompts/` and must not move the measurement version.

    The bundle version is the cache key and the thing `--final` pins against. If writing
    down *what a prompt change did* itself counted as a prompt change, every log line
    would invalidate the cache and the version would stop naming the prompts.
    """
    before = versions._compute_prompt_bundle_version()
    changelog = versions._PROMPTS_DIR / "CHANGELOG.md"
    existed = changelog.exists()
    original = changelog.read_bytes() if existed else None
    try:
        changelog.write_text((original.decode() if original else "") + "\nscratch line\n")
        assert versions._compute_prompt_bundle_version() == before
    finally:
        if original is None:
            changelog.unlink(missing_ok=True)
        else:
            changelog.write_bytes(original)


def test_an_actual_prompt_edit_does_move_the_bundle_version() -> None:
    """The other half: the exclusion must not have blunted the hash."""
    before = versions._compute_prompt_bundle_version()
    prompt = versions._PROMPTS_DIR / "classify_and_triage.md"
    original = prompt.read_bytes()
    try:
        prompt.write_bytes(original + b"\n<!-- scratch -->\n")
        assert versions._compute_prompt_bundle_version() != before
    finally:
        prompt.write_bytes(original)
