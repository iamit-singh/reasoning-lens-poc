"""Contract tests for the C2.2 package boundary rules.

The authoritative enforcement is ``.importlinter`` and ``scripts/check_provider_symbols.sh``
in CI. These tests duplicate it deliberately: a developer running ``pytest`` locally finds
out before pushing, and I1 is the invariant the whole architecture rests on.
"""

from __future__ import annotations

import ast
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

#: Top-level packages the analyzer may never import (I1).
FORBIDDEN_ROOTS = frozenset({"backend", "frontend", "problem_bank"})


def _imported_roots(source: str) -> set[str]:
    """The root package of every import in a module, via the AST.

    Parsed rather than grepped. A regex over the raw text cannot tell an import from
    prose that happens to begin with the word -- this module's own docstrings discuss
    `import problem_bank` precisely because that import is forbidden, and a text match
    flagged them. A false positive in a boundary test is not harmless: it trains whoever
    hits it to weaken the check, and this is the check the architecture rests on.
    """
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


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
        f"{path.relative_to(SRC)} -> {sorted(bad)}"
        for path in SRC.rglob("*.py")
        if (bad := _imported_roots(path.read_text()) & FORBIDDEN_ROOTS)
    ]
    assert not offenders, f"I1 violation -- analyzer imports non-analyzer code in: {offenders}"


@pytest.mark.contract
def test_the_c21_tree_exists() -> None:
    """Fixture directories are load-bearing: S2's reference span tree and the G1 report
    fixtures are named by tests that other people's work depends on."""
    for expected in ("fixtures/spans", "fixtures/reports"):
        assert (Path(__file__).parent / expected).is_dir(), f"missing {expected}"


@pytest.mark.contract
def test_the_import_check_would_actually_catch_a_violation() -> None:
    """The boundary test's own test.

    A detector that silently stops detecting is worse than no detector, and this one
    just changed implementation. Both halves matter: a real import is caught, and prose
    mentioning one is not -- the false positive that motivated the rewrite.
    """
    assert _imported_roots("from problem_bank.items import load") & FORBIDDEN_ROOTS
    assert _imported_roots("import backend.cache") & FORBIDDEN_ROOTS
    assert not _imported_roots('"""Docstring saying: import problem_bank."""') & FORBIDDEN_ROOTS
    assert not _imported_roots("import json\nfrom rlens.checkers import check") & FORBIDDEN_ROOTS
