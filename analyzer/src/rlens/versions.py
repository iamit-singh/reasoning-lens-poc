"""The versions that travel with every report and form the cache key.

Amended by ADR-001. For a hosted model the pin was an exact dated id. For a **local**
model an id does not reproduce a number -- the same tag can be re-pulled as different
weights, and sampling settings change the output -- so the generation pin is a *tuple*
and every field enters the cache key.

This is stricter than the hosted pin it replaces: a hosted endpoint can change under a
fixed id; a file digest cannot.

The analyzer's own pin is recorded separately, because generation (local) and analysis
(OpenAI) move independently.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

#: Bumped by hand when the Strategy Runner's arm construction changes.
RUNNER_VERSION = "0.1.0"

#: Bumped by hand when analyzer semantics change (segmenter, classifier, judge).
ANALYZER_VERSION = "0.1.0"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _compute_prompt_bundle_version() -> str:
    """Content hash over ``prompts/*.md``, sorted by name.

    Content-addressed so it cannot drift from the prompts it names: a prompt edit that
    forgets to bump the version fails CI rather than silently reusing a cache entry
    produced by different prompts.
    """
    digest = hashlib.sha256()
    for path in sorted(_PROMPTS_DIR.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


PROMPT_BUNDLE_VERSION = _compute_prompt_bundle_version()


@dataclass(frozen=True)
class GenerationPin:
    """The local generation model, pinned reproducibly (ADR-001).

    All three arms share one pin by construction. The arms compare reasoning *strategies*;
    different models per arm would measure vendors instead, and the finding evaporates.
    """

    model: str
    digest: str
    quantization: str
    runtime: str
    temperature: float
    top_p: float
    seed: int
    reasoning_effort: str

    def fingerprint(self) -> str:
        """Stable digest of every field. This is what enters the cache key."""
        parts = (
            self.model,
            self.digest,
            self.quantization,
            self.runtime,
            f"{self.temperature:g}",
            f"{self.top_p:g}",
            str(self.seed),
            self.reasoning_effort,
        )
        return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]

    def unpinned_fields(self) -> tuple[str, ...]:
        """Fields that must be filled before a number may be published.

        ``digest``, ``quantization`` and ``runtime`` are populated by ``make pin-local``;
        they are empty on a fresh checkout, and a report built on an empty pin is not
        reproducible -- so the pipeline refuses rather than publishing it.
        """
        missing = [
            name
            for name in ("model", "digest", "quantization", "runtime")
            if not getattr(self, name)
        ]
        return tuple(missing)


def generation_pin() -> GenerationPin:
    """Read the generation pin from the environment. See ``.env.example``."""
    return GenerationPin(
        model=os.environ.get("LOCAL_MODEL", ""),
        digest=os.environ.get("LOCAL_MODEL_DIGEST", ""),
        quantization=os.environ.get("LOCAL_QUANTIZATION", ""),
        runtime=os.environ.get("LOCAL_RUNTIME", ""),
        temperature=float(os.environ.get("GEN_TEMPERATURE", "0")),
        top_p=float(os.environ.get("GEN_TOP_P", "1.0")),
        seed=int(os.environ.get("GEN_SEED", "0")),
        reasoning_effort=os.environ.get("LOCAL_REASONING_EFFORT", ""),
    )


def analyzer_pin() -> str:
    """The exact dated OpenAI id doing the classification. Never a floating alias."""
    pin = os.environ.get("MODEL_ANALYZE", "")
    if not pin:
        raise RuntimeError(
            "MODEL_ANALYZE is unset. It must be an exact dated model id, never an alias -- "
            "see docs/decisions/ADR-001-provider.md."
        )
    if _is_alias(pin):
        raise RuntimeError(
            f"MODEL_ANALYZE={pin!r} looks like a floating alias. A number pinned to an "
            "alias expires silently; use the exact dated id."
        )
    return pin


def _is_alias(model: str) -> bool:
    """A floating alias resolves to different weights over time."""
    return "latest" in model or model.endswith(("-preview", "-turbo"))


def cache_key(
    item_id: str,
    strategy: str,
    *,
    gen: GenerationPin | None = None,
    analyze: str | None = None,
) -> str:
    """The cache key. A change to any input invalidates the entry.

    A change to the *generation* pin additionally requires re-running the calibration
    harness and the faithfulness batch job -- agreement and hint-verbalisation rates are
    model-specific, and the local pin now includes sampling settings that change output.
    """
    generation = gen if gen is not None else generation_pin()
    parts = (
        item_id,
        strategy,
        RUNNER_VERSION,
        generation.fingerprint(),
        analyze if analyze is not None else analyzer_pin(),
        ANALYZER_VERSION,
        PROMPT_BUNDLE_VERSION,
        os.environ.get("ANALYZER_BACKEND", "hybrid"),
    )
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()
