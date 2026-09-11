#!/usr/bin/env python3
"""Draw the calibration sample — the random-90 half of C5.1's two-part frame.

    make draw-sample            # writes the ordered id list into calibration/sampling.json
    make draw-sample ARGS="--force"   # redraw. Refuses if labels already exist.

**This runs exactly once, before the first label is written, and Hazard 2 is the reason.**
`step_id` embeds the segmenter's ordinal. A draw taken against one segmenter freeze names
different text under another, so the draw and the freeze are recorded in the same file and
a redraw after labelling has begun is a request to re-label.

The two halves, and why only one of them can be drawn today
-----------------------------------------------------------
C5.1 splits the calibration set in two:

* **random-90** — a uniform random draw over the step population. **This is the one that
  carries the published kappa**, because it is the only one whose sampling is independent
  of anything the classifier did.
* **enriched-60** — deliberately over-sampled from classes the classifier says are rare, so
  that per-class F1 has enough instances to be computable at all. It needs the classifier's
  predictions, so it cannot be drawn until Month 2 (M2-14).

Drawing early labels from the enriched half would bias the very kappa the two-part frame
exists to protect. Hence: the first 40 labels come from random-90, in seeded order.

What is in the population, and what is deliberately not
------------------------------------------------------
Every `thought`, `tool_call` and `observation` step in the corpus. **`answer` steps are
excluded**, and that is a judgement worth stating rather than burying:

* An answer step is the model's *output*, not a reasoning move. It is `linear` by
  construction in almost every trace.
* Including it would inflate raw agreement and the majority-class baseline together,
  without measuring anything about the rubric.

The cost of the exclusion is real and is recorded here: the classifier *does* emit a row
for answer steps, and those rows are outside the measured population. The calibration page
must say so rather than implying kappa covers every row the classifier writes.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))

from rlens.ingest import otel  # noqa: E402
from rlens.segment import segment  # noqa: E402

SPANS = ROOT / "out/spans"
SAMPLING = ROOT / "calibration/sampling.json"
LABELS = ROOT / "calibration/labels"

#: C5.1. 90 uniform + 60 enriched; the first 40 of the 90 are M1-11's, the rest M2-1.
RANDOM_N = 90

#: The kinds a human is asked to label. See the module docstring for the exclusion.
LABELLED_KINDS = ("thought", "tool_call", "observation")


def population() -> list[dict[str, str]]:
    """Every labellable step in the corpus, in a deterministic order.

    Sorted by `(trace, ordinal)` before the shuffle so the draw depends only on the seed
    and not on the order the filesystem happened to list the span trees in. A draw that
    varies with directory iteration order is not reproducible from its seed, which is the
    only property it needs to have.
    """
    steps: list[dict[str, str]] = []
    for path in sorted(SPANS.glob("*.json")):
        trace = segment(otel.parse(json.loads(path.read_text())))
        for step in trace.steps:
            if step.kind in LABELLED_KINDS:
                steps.append(
                    {
                        "step_id": step.step_id,
                        "item_id": trace.item_id,
                        "strategy": trace.strategy,
                        "kind": step.kind,
                    }
                )
    steps.sort(key=lambda s: (s["item_id"], s["strategy"], s["step_id"]))
    return steps


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260930, help="the committed draw seed")
    ap.add_argument("--force", action="store_true", help="redraw even if a draw exists")
    args = ap.parse_args(argv)

    if not SPANS.is_dir():
        print(f"no span trees at {SPANS}. Run `make spans` first.", file=sys.stderr)
        return 2

    record = json.loads(SAMPLING.read_text())
    existing = record.get("draw", {}).get("seed")
    written = sorted(LABELS.glob("*.jsonl"))
    if existing is not None and not args.force:
        print(
            f"a draw already exists (seed {existing}). Re-drawing after labelling has begun "
            f"re-labels every affected step (Hazard 2). Pass --force if that is intended.",
            file=sys.stderr,
        )
        return 2
    if written and args.force:
        # The one case --force must still refuse. A redraw under existing labels produces a
        # label file whose rows came from two different populations, and nothing downstream
        # can tell which row came from which.
        print(
            f"--force refused: {len(written)} label file(s) already exist "
            f"({', '.join(p.name for p in written)}). A redraw now would mix two draws in "
            f"one dataset. Move them aside deliberately if the redraw is really intended.",
            file=sys.stderr,
        )
        return 2

    pool = population()
    if len(pool) < RANDOM_N:
        print(
            f"only {len(pool)} labellable steps in the corpus; the draw needs {RANDOM_N}.",
            file=sys.stderr,
        )
        return 2

    rng = random.Random(args.seed)
    drawn = rng.sample(pool, RANDOM_N)

    record["draw"] = {
        "owner": "M1-11 (W4)",
        "seed": args.seed,
        "drawn_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": _git_sha(),
        "method": (
            f"random.Random({args.seed}).sample(population, {RANDOM_N}) over every "
            f"{'/'.join(LABELLED_KINDS)} step in out/spans, sorted by "
            f"(item_id, strategy, step_id) before the draw so the result depends on the "
            f"seed alone and not on filesystem order."
        ),
        "part": "random-90 of C5.1's two-part frame. The enriched-60 needs the "
        "classifier's predictions and is drawn in M2-14; drawing early labels from it "
        "would bias the very kappa the two-part frame protects.",
        "population_size": len(pool),
        "population_kinds": list(LABELLED_KINDS),
        "population_note": (
            "`answer` steps are EXCLUDED: an answer step is the model's output rather than "
            "a reasoning move and is `linear` by construction, so including it would "
            "inflate raw agreement and the majority-class baseline together. The "
            "classifier does emit rows for answer steps; those rows are outside the "
            "measured population and the calibration page must say so."
        ),
        "first_40_are": "M1-11's pass, in the order below. M2-1 labels the remaining 50.",
        "ordered_step_ids": [s["step_id"] for s in drawn],
    }
    SAMPLING.write_text(json.dumps(record, indent=2) + "\n")

    from collections import Counter

    print(f"drew {RANDOM_N} of {len(pool)} labellable steps with seed {args.seed}")
    print(f"  by strategy {dict(Counter(s['strategy'] for s in drawn))}")
    print(f"  by kind     {dict(Counter(s['kind'] for s in drawn))}")
    print(f"  -> {SAMPLING}")
    print("\nCOMMIT THIS FILE BEFORE WRITING THE FIRST LABEL (Hazard 2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
