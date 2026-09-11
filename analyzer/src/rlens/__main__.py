"""``python -m rlens`` -- the Month-1 milestone CLI.

Target shape:
    python -m rlens --item X --all-arms
        -> three OTEL span trees -> segmented, classified steps -> a ReasoningReport

**Owner: M1-10**, which is where `pipeline.analyze(span_tree) -> ReasoningReport` lands
and where G1 freezes the output contract. M1-0 placed this entry point so `pyproject`
scripts, the Makefile targets and the integration-mock CI job all address a real module
from Week 1.

Two thirds of the chain exist already and are reachable today, which is what this says
rather than claiming a task that has shipped:

* `python -m rlens.runner --item X --all-arms` writes the three span trees (M1-6, M1-7).
* `rlens.segment.segment(rlens.ingest.otel.parse(tree))` segments one (M1-8, frozen).

What is missing is the classifier (M1-9) and the report assembly (M1-10).
"""

from __future__ import annotations

import sys

HELP = """\
rlens: the end-to-end pipeline is not implemented yet (owner: M1-10, W4).

What works today:
  python -m rlens.runner --item mb-08 --all-arms   # span trees for all three arms
  make spans                                       # replay every item from cassettes

Missing: the behavior classifier (M1-9) and ReasoningReport assembly (M1-10, G1).
"""


def main(argv: list[str] | None = None) -> int:
    """Placeholder entry point. Non-zero until M1-10 lands, deliberately: a CLI that
    exited 0 while doing nothing would pass the integration-mock job by accident."""
    args = sys.argv[1:] if argv is None else argv
    sys.stderr.write(HELP)
    if args:
        sys.stderr.write(f"received: {args!r}\n")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
