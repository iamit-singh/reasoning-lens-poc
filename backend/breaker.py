"""The spend breaker and the demo-safety switch — C9, decided by ADR-011.

Owner: M3-3.

**The breaker fails closed, and the interesting branch is the third one.** There are not
two outcomes here (under limit / over limit) but four, and the one that earns this module
its own file is *we could not read the spend total*:

    file readable, under limit ....... allow
    file readable, at/over limit ..... DENY, tripped
    file missing ..................... allow  -- a fresh install has spent nothing
    file unreadable or malformed ..... DENY  -- and this is the point

*"We could not read it"* must never resolve to *"so assume zero"*. That resolution buys an
unbounded run off a corrupted file. This project has now written the same sentence about a
trace it could not read (`trace_quality`), an answer it could not parse (`unparsed`), and
an arm whose classifier failed (`degraded`): **the third outcome gets its own branch
instead of collapsing into the nearest convenient lie.** This is the fourth time, and the
first where the lie would cost money rather than accuracy.

A *missing* file is deliberately not the same as an unreadable one. Denying on missing
would make a fresh checkout born tripped, and the first thing any operator would learn is
how to bypass the breaker — which is a worse security posture than not having one.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _spend_file() -> pathlib.Path:
    """Where the running total lives. A file, not a service (ADR-011).

    **An empty `SPEND_FILE` falls back to the default rather than becoming the cwd.**
    `pathlib.Path("")` is `.`, a directory, so `os.environ.get(name, default)` — which
    returns `""` for a variable that is *set but blank* — silently pointed the breaker at
    the working directory. `.env.example` ships this key blank to document it, so blank is
    the common case, not an edge one.

    The smoke test found this, and the way it found it is the argument for failing closed:
    the breaker denied every live run with `IsADirectoryError` instead of reading a
    zero total and allowing them. A fail-open breaker would have passed the smoke test.
    """
    return pathlib.Path(os.environ.get("SPEND_FILE") or str(ROOT / "out/spend.json"))


#: Resolved once at import. Module-level rather than per-call so a test can point it at a
#: tmpdir with a single `monkeypatch.setattr`, and so the path a run used is the path it
#: keeps — a breaker whose file location can move mid-process is not a breaker.
SPEND_FILE = _spend_file()


@dataclass(frozen=True)
class BreakerState:
    """Why the breaker said what it said. The reason travels with the verdict.

    A bare boolean would make the operator-facing message *"live runs are unavailable"*,
    which is indistinguishable between "you have spent your budget" and "your spend file
    has a typo in it". Those need different actions, so they are different reasons.
    """

    allowed: bool
    reason: str
    spent_usd: float | None
    limit_usd: float


def limit_usd() -> float:
    return float(os.environ.get("SPEND_BREAKER_USD", "10"))


def alarm_usd() -> float:
    return float(os.environ.get("SPEND_ALARM_USD", "5"))


def read_spend() -> tuple[float | None, str]:
    """The running total, or None with a reason if it could not be read.

    `None` means *unknown*, never *zero*. Every caller must treat the two differently, and
    the type is what forces them to.
    """
    if not SPEND_FILE.exists():
        return 0.0, "no spend recorded yet"
    try:
        raw = json.loads(SPEND_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"spend file unreadable: {type(exc).__name__}"
    if not isinstance(raw, dict):
        return None, "spend file is not an object"
    value = raw.get("usd")
    # `True` is an int in Python, and a spend file holding `true` must not read as $1.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, f"spend file has a non-numeric total: {value!r}"
    return float(value), "ok"


def check() -> BreakerState:
    """Ask the breaker. **Call this before anything that can spend.**"""
    limit = limit_usd()
    spent, reason = read_spend()
    if spent is None:
        return BreakerState(
            allowed=False,
            reason=(
                f"breaker tripped: {reason}. Failing CLOSED — an unreadable total is not "
                f"a zero total (ADR-011). Fix or delete {SPEND_FILE.name} to reset."
            ),
            spent_usd=None,
            limit_usd=limit,
        )
    if spent >= limit:
        return BreakerState(
            allowed=False,
            reason=f"breaker tripped: ${spent:.2f} spent against a ${limit:.2f} limit",
            spent_usd=spent,
            limit_usd=limit,
        )
    return BreakerState(allowed=True, reason="ok", spent_usd=spent, limit_usd=limit)


def record(usd: float) -> float:
    """Add to the running total and return the new one.

    Read-modify-write with no lock, which ADR-011 names as the cost of dropping Redis: two
    processes racing here could interleave. There is one process, and the failure mode if
    that ever stopped being true is that the breaker trips slightly late.
    """
    spent, _ = read_spend()
    total = (spent or 0.0) + usd
    SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    SPEND_FILE.write_text(json.dumps({"usd": round(total, 6)}, indent=2) + "\n")
    return total


def trip(reason: str = "forced") -> None:
    """Trip the breaker deliberately. **This is M3-3's DoD, as a function.**

    The DoD asks for a *forced trip*, not for a reader to be convinced the code is right.
    Having it as a callable — used by `make trip-breaker` and by the test — means the
    demonstration is the same code path the real limit takes, rather than a simulation of
    it.
    """
    SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    SPEND_FILE.write_text(
        json.dumps({"usd": limit_usd() + 1.0, "tripped_by": reason}, indent=2) + "\n"
    )


def reset() -> None:
    """Clear the total. Separate from `trip` so neither is a mode of the other."""
    if SPEND_FILE.exists():
        SPEND_FILE.unlink()
