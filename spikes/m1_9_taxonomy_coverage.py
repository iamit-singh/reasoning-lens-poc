#!/usr/bin/env python3
"""Does the corpus contain the behaviours the taxonomy names? — M1-9, W4.

    make taxonomy-coverage

**This exists to stop a wrong conclusion being drawn from a true number.** The classifier
assigned `backtracking` to 0 of 310 steps across the bank x 3 arms. The tempting reading is
*"this model does not backtrack"*, which would be a claim about the model. The other
reading is *"the classifier does not detect backtracking"*, which would be a claim about
the classifier. **They have opposite consequences** — one re-scopes the corpus, the other
is a prompt-quality problem that M2-3 exists to fix — and nothing in the classifier's own
output can tell them apart.

So this measures the corpus **without a model**: how many steps open with a surface marker
that C4.2's own segmenter already treats as a discourse signal. It is a lower bound on
opportunity, not a labelling — a step that opens with "Wait" may or may not be
`backtracking`, and the rubric's hard case 4.2 says explicitly that a `wait` which reverses
nothing is `linear`.

That is the point. **This script narrows the question; it does not answer it.** The only
thing that can answer it is a human reading the steps, which is M1-11 — and that makes the
40 labels the most valuable 1.5 hours left in Month 1 rather than a box to tick.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))

from rlens.ingest import otel  # noqa: E402
from rlens.segment import segment  # noqa: E402

SPANS = ROOT / "out/spans"

#: Surface markers, anchored to the START of a step. Anchored because the segmenter splits
#: *before* a discourse marker (C4.2 §2c), so a step that is a backtrack begins with one --
#: and an unanchored search would match the word anywhere and count discussion of the idea
#: as an instance of it.
#:
#: These are deliberately NOT the classifier's definitions. They are the cheapest possible
#: proxy for "a human reading this step would at least pause over it".
SIGNALS: dict[str, str] = {
    "backtracking": (
        r"^(wait|actually|hold on|hmm,? no|that'?s wrong|no,|but wait|"
        r"let me try (a )?different|instead|on second thought|scratch that)"
    ),
    "verification": (
        r"^(check|verify|let me check|let me verify|double[- ]check|confirm|recompute|sanity)"
    ),
    "subgoal_setting": (
        r"^(first|first,? I|step 1|to (start|begin)|I need to|let'?s start|begin by)"
    ),
    "backward_chaining": (
        r"^(to get|for the answer|working backward|what I (ultimately )?need|the answer must)"
    ),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--examples", type=int, default=3, help="examples to print per class")
    args = ap.parse_args(argv)

    if not SPANS.is_dir():
        print(f"no span trees at {SPANS}. Run `make spans` first.", file=sys.stderr)
        return 2

    counts: collections.Counter[str] = collections.Counter()
    examples: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    by_trace: collections.Counter[str] = collections.Counter()
    total = 0

    for path in sorted(SPANS.glob("*.json")):
        trace = segment(otel.parse(json.loads(path.read_text())))
        name = path.name.removesuffix(".json")
        for step in trace.steps:
            if step.kind != "thought":
                continue
            total += 1
            head = step.text.strip()
            for label, pattern in SIGNALS.items():
                if re.match(pattern, head, re.I):
                    counts[label] += 1
                    by_trace[f"{label}:{name}"] += 1
                    if len(examples[label]) < args.examples:
                        examples[label].append((name, head[:100]))
                    break

    print(f"{total} thought steps across {len(list(SPANS.glob('*.json')))} traces\n")
    print(f"  {'class':20s} {'steps with a surface marker':>28s}")
    for label in SIGNALS:
        share = 100 * counts[label] / total if total else 0
        print(f"  {label:20s} {counts[label]:14d}  ({share:.1f}%)")

    for label, rows in examples.items():
        print(f"\n--- {label} ---")
        for name, text in rows:
            print(f"   [{name}] {text}")

    spread = collections.Counter()
    for key in by_trace:
        spread[key.split(":", 1)[0]] += 1
    print(f"\n  traces containing each signal: {dict(spread)}")
    print(
        "\n  A surface marker is a LOWER BOUND on opportunity, not a label. rubric.md hard\n"
        "  case 4.2 adjudicates a `wait` that reverses nothing as `linear`, and several of\n"
        "  these are exactly that. Only a human reading them settles it — that is M1-11."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
