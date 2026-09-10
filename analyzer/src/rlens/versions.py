"""The four versions that travel with every report and form the cache key (C2.3).

A change to any of the four invalidates the cache and requires a warm-cache run.
A change to ``MODEL_PIN`` additionally requires re-running the calibration harness
and the faithfulness batch job (B7.4) -- kappa and hint-verbalisation rates are
model-version-specific.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

#: Bumped by hand when the Strategy Runner's arm construction changes (M1-6, M1-7).
RUNNER_VERSION = "0.1.0"

#: Bumped by hand when analyzer semantics change (segmenter, classifier, judge).
ANALYZER_VERSION = "0.1.0"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _compute_prompt_bundle_version() -> str:
    """Content hash over ``prompts/*.md``, sorted by name.

    CI asserts this value matches the committed one, so any prompt edit that forgets
    to bump the bundle version fails the build rather than silently reusing a cache
    entry produced by a different prompt (C2.3).
    """
    digest = hashlib.sha256()
    for path in sorted(_PROMPTS_DIR.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


#: Content-addressed, so it cannot drift from the prompts it names.
PROMPT_BUNDLE_VERSION = _compute_prompt_bundle_version()


def model_pin() -> str:
    """The exact dated generation-model id. Never a floating alias (C2.3, G0 check 4).

    Read at call time rather than import time so tests can pin it without reimporting.
    """
    pin = os.environ.get("MODEL_PIN", "")
    if not pin:
        raise RuntimeError(
            "MODEL_PIN is unset. It must be an exact dated model id, never an alias -- "
            "see docs/decisions/ADR-001-provider.md."
        )
    return pin


def cache_key(item_id: str, strategy: str, *, pin: str | None = None) -> str:
    """CACHE_KEY = sha256(item_id, strategy, RUNNER_VERSION, MODEL_PIN, ANALYZER_VERSION,
    PROMPT_BUNDLE_VERSION) -- C2.3."""
    parts = (
        item_id,
        strategy,
        RUNNER_VERSION,
        pin if pin is not None else model_pin(),
        ANALYZER_VERSION,
        PROMPT_BUNDLE_VERSION,
    )
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()
