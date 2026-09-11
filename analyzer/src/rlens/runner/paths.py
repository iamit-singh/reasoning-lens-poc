"""Where the repo's *data* lives, resolved without depending on the current directory.

Owner: M1-7.

**Why this exists.** `problem-bank/items` and `problem-bank/corpus/facts.json` were both
written as bare relative paths. That works from the repo root, which is where the CLI is
always run, and fails everywhere else — `make test` runs pytest from `analyzer/`, so the
first test to actually load the corpus could not find it.

The defect is worth naming rather than patching, because of *how* it would have surfaced.
The corpus is only read by arm 3, and a missing corpus raises a `ToolError` inside a tool
call, which the loop is designed to swallow into an observation. From anywhere but the repo
root, arm 3 would have run, called `lookup`, received `no fact corpus at ...` as a well-
formed observation, reported it honestly, and answered wrong — a *green* run with a
plausible chain explaining why it could not find the fact. This module is the reason that
cannot happen quietly: resolution is explicit, and a failure names every place it looked.

I1 is unaffected. The bank and the corpus stay **runtime inputs read as data** — this
resolves a path, it does not import `problem_bank`.
"""

from __future__ import annotations

import os
import pathlib

#: `<repo>/analyzer/src/rlens/runner/paths.py` -> `<repo>`. Used only as a fallback when
#: the data is not found relative to the working directory, so a checkout behaves the same
#: from any directory inside it.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]


def data_path(relative: str, *, env_var: str | None = None) -> pathlib.Path:
    """Resolve a repo-data path: the env override, then the cwd, then the checkout.

    The order matters. An explicit `env_var` must win, or a deliberately pointed-at corpus
    or bank could be silently overridden by whatever happens to sit next to the checkout —
    which is how a run gets measured against data nobody chose.
    """
    override = os.environ.get(env_var) if env_var else None
    if override:
        return pathlib.Path(override)
    local = pathlib.Path(relative)
    if local.exists():
        return local
    return _REPO_ROOT / relative


def missing_data_message(relative: str, env_var: str) -> str:
    """Say where we looked. A path error that names one location is a guessing game."""
    return (
        f"could not find {relative}. Looked at {pathlib.Path(relative).resolve()} "
        f"and {_REPO_ROOT / relative}. Set {env_var} to point at it explicitly."
    )
