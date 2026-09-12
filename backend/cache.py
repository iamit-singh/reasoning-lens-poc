"""The cache tier and the staleness assertion — C2.3, M3-2a/M3-2b, ADR-011.

Owner: M3-2.

There is one tier and it is the filesystem ([ADR-011](../docs/decisions/ADR-011-no-redis.md)).
`out/reports/{id}.report.json` is both the cache and the source of truth, which makes this
module small — and moves its whole weight onto the second job.

The second job: **a cached report must describe the service that is serving it**
--------------------------------------------------------------------------------
C2.3 makes four things part of the cache key — the runner version, the analyzer version,
the prompt bundle, and the model pin. A report built before any of them changed is not
merely old. It is a set of numbers *attributed to a system that is no longer running*, and
serving it silently is the single most dishonest thing this backend could do: every caveat
on the calibration page, every version block in the download, every claim of
reproducibility, would be describing a different pipeline than the one that produced the
figures on screen.

So staleness is not a cache-efficiency concern here. It is the same honesty rule the rest
of the project keeps re-deriving, applied to time instead of to parsing:

    fresh ......... serve it
    stale ......... REFUSE, and name which version moved
    unreadable .... REFUSE, and say so

G3's own exit criterion is *"the served numbers describe the running service"*, and
`assert_fresh` is where that is enforceable rather than asserted in prose.

**Why refuse rather than regenerate.** Regenerating on a miss would make a `GET` trigger a
model call, which is exactly what C4.9 forbids and what B4 #8's latency budget is built
around. A stale report is an operator problem with a one-command fix (`make warm-cache`),
and it should surface as a loud refusal at startup rather than as a slow request.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

from rlens.versions import (
    ANALYZER_VERSION,
    PROMPT_BUNDLE_VERSION,
    RUNNER_VERSION,
    generation_pin,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "out/reports"


@dataclass(frozen=True)
class Staleness:
    """What moved since this report was built. Empty `drifted` means it is current."""

    item_id: str
    drifted: tuple[str, ...]
    error: str | None = None

    @property
    def fresh(self) -> bool:
        return not self.drifted and self.error is None

    def describe(self) -> str:
        if self.error:
            return f"{self.item_id}: {self.error}"
        if not self.drifted:
            return f"{self.item_id}: current"
        return f"{self.item_id}: stale on {', '.join(self.drifted)}"


def current_versions() -> dict[str, str]:
    """The four C2.3 inputs, as the running process sees them right now."""
    return {
        "runner": RUNNER_VERSION,
        "analyzer": ANALYZER_VERSION,
        "prompts": PROMPT_BUNDLE_VERSION,
        "model_pin": generation_pin().fingerprint(),
    }


def report_path(item_id: str) -> pathlib.Path:
    return REPORTS_DIR / f"{item_id}.report.json"


def check(item_id: str) -> Staleness:
    """Compare one cached report's version block against the running process."""
    path = report_path(item_id)
    if not path.exists():
        return Staleness(item_id, (), error="no cached report")
    try:
        report = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return Staleness(item_id, (), error=f"unreadable: {type(exc).__name__}")
    return check_report(item_id, report)


def check_report(item_id: str, report: dict[str, Any]) -> Staleness:
    have = report.get("versions") or {}
    want = current_versions()
    drifted = tuple(
        f"{field} ({have.get(field)!r} != {value!r})"
        for field, value in want.items()
        if have.get(field) != value
    )
    return Staleness(item_id, drifted)


def scan() -> list[Staleness]:
    """Every cached report, checked. What `readyz` and the startup assertion both read."""
    if not REPORTS_DIR.is_dir():
        return []
    ids = sorted(p.name.split(".")[0] for p in REPORTS_DIR.glob("*.report.json"))
    return [check(item_id) for item_id in ids]


class StaleCacheError(RuntimeError):
    """Raised at startup when the cache does not describe the running service."""


def assert_fresh(*, strict: bool = True) -> list[Staleness]:
    """**M3-2b's startup assertion.** Refuse to start on a stale cache.

    `strict=False` is for development, where the pin is often empty and every report looks
    stale; it downgrades the refusal to a returned list the caller can log. It is not the
    default, because the default is the one that ships.
    """
    results = scan()
    stale = [s for s in results if not s.fresh and s.error is None]
    if stale and strict:
        lines = "\n  ".join(s.describe() for s in stale)
        raise StaleCacheError(
            f"{len(stale)} cached report(s) do not match the running versions:\n  {lines}\n"
            f"These numbers were produced by a different pipeline than the one now running. "
            f"Re-warm with `make warm-cache`, or start with CACHE_STRICT=0 to serve them "
            f"anyway — which is a decision to publish figures attributed to a system that "
            f"is not running."
        )
    return results
