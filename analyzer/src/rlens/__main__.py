"""``python -m rlens`` -- the Month-1 milestone CLI.

Target shape (M1-6, M1-7):
    python -m rlens --item X --all-arms
        -> three OTEL span trees -> segmented, classified steps -> a ReasoningReport

Owner: M1-6. M1-0 places the entry point so ``pyproject`` scripts, the Makefile
targets and the integration-mock CI job all address a real module from Week 1.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Placeholder entry point. Returns a non-zero exit code until M1-6 lands."""
    args = sys.argv[1:] if argv is None else argv
    sys.stderr.write(f"rlens CLI is not implemented yet (owner: M1-6, W2).\nreceived: {args!r}\n")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
