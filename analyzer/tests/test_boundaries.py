"""Contract tests for the C2.2 package boundary rules.

The authoritative enforcement is ``.importlinter`` and ``scripts/check_provider_symbols.sh``
in CI. These tests duplicate it deliberately: a developer running ``pytest`` locally finds
out before pushing, and I1 is the invariant the whole architecture rests on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "rlens"

#: Modules that may never mention a provider SDK symbol (C2.2 rule 2).
PROVIDER_FREE_MODULES = ("segment.py", "classify.py", "judge.py", "consistency.py")

#: Modules where provider payload shapes are permitted.
PROVIDER_ALLOWED = ("llm.py", "ingest/otel.py")

PROVIDER_SYMBOLS = re.compile(
    r"\b(anthropic|openai|OpenAI|Anthropic|google\.generativeai|genai|mistralai|cohere|ollama)\b"
)

FORBIDDEN_IMPORTS = re.compile(
    r"^\s*(?:from|import)\s+(backend|frontend|problem_bank|problem-bank)\b", re.M
)


@pytest.mark.contract
@pytest.mark.parametrize("module", PROVIDER_FREE_MODULES)
def test_no_provider_symbols_outside_llm_and_ingest(module: str) -> None:
    text = (SRC / module).read_text()
    found = PROVIDER_SYMBOLS.findall(text)
    assert not found, (
        f"{module} references provider symbols {found}; allowed only in {PROVIDER_ALLOWED}"
    )


@pytest.mark.contract
def test_analyzer_never_imports_backend_or_bank() -> None:
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if FORBIDDEN_IMPORTS.search(path.read_text())
    ]
    assert not offenders, f"I1 violation -- analyzer imports non-analyzer code in: {offenders}"


@pytest.mark.contract
def test_the_c21_tree_exists() -> None:
    """Fixture directories are load-bearing: S2's reference span tree and the G1 report
    fixtures are named by tests that other people's work depends on."""
    for expected in ("fixtures/spans", "fixtures/reports"):
        assert (Path(__file__).parent / expected).is_dir(), f"missing {expected}"
