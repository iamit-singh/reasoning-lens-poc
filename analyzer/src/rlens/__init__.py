"""Reasoning Lens analyzer.

Invariant I1: this package's only input is an OTEL/OpenInference span tree, and it
must not import from ``backend``, ``problem-bank`` or any web code. The rule is
enforced by the ``.importlinter`` contract in CI, not by convention.
"""

from rlens.versions import (
    ANALYZER_VERSION,
    PROMPT_BUNDLE_VERSION,
    RUNNER_VERSION,
    GenerationPin,
    analyzer_pin,
    cache_key,
    generation_pin,
)

__all__ = [
    "ANALYZER_VERSION",
    "PROMPT_BUNDLE_VERSION",
    "RUNNER_VERSION",
    "GenerationPin",
    "analyzer_pin",
    "cache_key",
    "generation_pin",
]
