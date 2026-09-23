#!/usr/bin/env python3
"""Every command the runbook prints must exist. Run: `make runbook-check` (in CI).

Owner: M3-5c / E13.

**This is the half of the peer dry-run a machine can do, and it is the half that was
actually finding things.** Of the nine defects two cold runs found in `runbook.md`, eight
were *exit codes* — a target that did not exist, a flag the document never learned, a
procedure that named `fe-build` where the demo ships `fe-build-measured`. A command that
exits 2 exits 2 for a peer too, and none of that needed a person to discover. It needed
somebody to run the commands from a clean checkout, which happened twice, by hand, five
days apart.

So the mechanical half becomes a check that runs on every PR, and the runbook stops being
able to drift from the Makefile silently.

**What this does NOT do, stated plainly so the row is not mistaken for closed.** E13 asks
whether *another team member* can drive the document. That is a question about
comprehension — whether the steps are in an order a stranger can follow, whether a
procedure assumes knowledge it never states, whether the reader gets stuck and gives up.
**None of that is checkable here**, and this check passing says nothing about it. What it
removes is the class of failure where a peer's dry-run is spent discovering that a command
was renamed six weeks ago — which is a waste of the scarcest resource this project has.

> **The dry-run is still owed and is still U2's.** This makes it cheaper and more
> informative, not unnecessary.

Why it checks existence rather than executing
---------------------------------------------
Several documented commands cost real money (`make seeded-errors`, `make
classify-reliability`, `make live-latency`), one pulls 13 GB (`make models`), and one
records a video. A check that ran them would be a check nobody could afford to run on every
PR, which makes it a check that gets disabled — and a disabled check is how
`.github/workflows` ended up with `if: false` on every measurement job until W5.

So this asserts the *referent* exists: the make target is real, the script is on disk, the
env var is in `.env.example`. That is exactly the failure mode the cold runs hit.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNBOOK = ROOT / "docs/runbook.md"
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"

ALL_FLAGS: set[str] = set()

#: Commands that belong to the world rather than to this repo. Their existence is not ours
#: to assert, and pretending otherwise would fail CI on a machine without Docker.
EXTERNAL = {
    "brew",
    "ollama",
    "docker",
    "curl",
    "playwright",
    "git",
    "cd",
    "export",
    "open",
    "pip",
    "python",
    "python3",
    "npm",
    "npx",
    "source",
    "echo",
    "cat",
    "ls",
}


def make_targets() -> set[str]:
    """Every target the Makefile defines, read from the Makefile rather than a list here."""
    text = MAKEFILE.read_text()
    return set(re.findall(r"^([a-zA-Z0-9_-]+):", text, flags=re.MULTILINE))


def env_keys() -> set[str]:
    if not ENV_EXAMPLE.exists():
        return set()
    return {
        m.group(1)
        for line in ENV_EXAMPLE.read_text().splitlines()
        if (m := re.match(r"^([A-Z0-9_]+)=", line.strip()))
    }


def all_flags() -> set[str]:
    """Every long option any script or module in this repo declares."""
    found: set[str] = set()
    # `spikes/` is in this list because leaving it out made the check's FIRST run report two
    # false positives -- `--only` and `--runs`, both real flags on spike harnesses the
    # runbook documents. A checker that cries wolf is one people learn to skip, which is the
    # argument M2-11's kappa comment makes for refusing to call "not yet measured" a failure.
    for base in ("scripts", "backend", "analyzer/src", "spikes"):
        for path in (ROOT / base).rglob("*.py"):
            found |= set(re.findall(r'add_argument\(\s*"(--[a-z][a-z0-9-]+)"', path.read_text()))
    return found


def commands() -> list[tuple[int, str]]:
    """Every command line inside a fenced block, with its line number."""
    out: list[tuple[int, str]] = []
    fenced = False
    for n, raw in enumerate(RUNBOOK.read_text().splitlines(), 1):
        if raw.startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            continue
        line = raw.split("#", 1)[0].strip()  # drop trailing comments
        if line:
            out.append((n, line))
    return out


def main() -> int:
    targets = make_targets()
    keys = env_keys()
    global ALL_FLAGS
    ALL_FLAGS = all_flags()
    failures: list[str] = []
    checked = {"make": 0, "script": 0, "env": 0, "flag": 0}

    for lineno, line in commands():
        # Strip leading `VAR=value` env prefixes: `DEMO_MODE=live MOCK_LLM=0 make serve-api`
        words = line.split()
        while words and re.fullmatch(r"[A-Z0-9_]+=\S*", words[0]):
            var = words[0].split("=", 1)[0]
            if keys and var not in keys and var not in {"PY", "PORT", "ARGS"}:
                failures.append(
                    f"{RUNBOOK.name}:{lineno} sets {var}=, which is in no documented "
                    f"environment. Add it to .env.example or stop telling people to set it."
                )
            checked["env"] += 1
            words = words[1:]
        if not words:
            continue

        head = words[0]
        if head in EXTERNAL or head.startswith(("./", "/", "$", "<")):
            # `./scripts/x.sh` is ours and is checked below; anything else external is not.
            if head.startswith("./"):
                path = ROOT / head[2:]
                checked["script"] += 1
                if not path.exists():
                    failures.append(f"{RUNBOOK.name}:{lineno} runs {head}, which is not on disk")
            continue

        if head == "make":
            for tgt in words[1:]:
                if "=" in tgt:  # ARGS="..." and friends
                    break
                checked["make"] += 1
                if tgt not in targets:
                    failures.append(
                        f"{RUNBOOK.name}:{lineno} runs `make {tgt}`, which the Makefile does "
                        f"not define. This is the defect class both cold runs kept finding."
                    )
            # **Documented flags must exist somewhere.** `make report ARGS="--all"` is only
            # useful advice while `--all` is still a flag; a renamed one leaves the runbook
            # confidently telling an operator to pass something argparse will reject. Checked
            # against every `add_argument` in the repo rather than against the one script
            # this target happens to call, because resolving a make recipe to its module is
            # a second parser to get wrong -- the looser check still catches a rename, which
            # is the failure being guarded.
            for flag in re.findall(r"(?<![\w-])--[a-z][a-z0-9-]+", line):
                checked["flag"] += 1
                if flag not in ALL_FLAGS:
                    failures.append(
                        f"{RUNBOOK.name}:{lineno} documents `{flag}`, which no argparse "
                        f"definition in this repo declares. Renamed, or never existed."
                    )
            continue

        # Anything referencing a repo path must point at something real.
        for word in words:
            if word.startswith(("scripts/", "backend/", "analyzer/", "docs/", "frontend/")):
                checked["script"] += 1
                if not (ROOT / word).exists():
                    failures.append(f"{RUNBOOK.name}:{lineno} names {word}, which is not on disk")

    print(
        f"runbook-check: {checked['make']} make targets, {checked['flag']} flags, "
        f"{checked['script']} paths, {checked['env']} env assignments, "
        f"from {RUNBOOK.relative_to(ROOT)}"
    )
    if failures:
        print("\nrunbook-check FAIL:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\n  These are the *mechanical* defects a peer dry-run should never be spent on.\n"
            "  E13's real question -- can somebody else follow this? -- is not affected either\n"
            "  way, and is still owed.",
            file=sys.stderr,
        )
        return 1
    print("runbook-check: OK -- every documented command exists (E13's mechanical half)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
