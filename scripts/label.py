#!/usr/bin/env python3
"""The blind labelling tool — M1-11, C5.2.

    make label                      # label the next unlabelled step in the queue
    make label ARGS="--count 10"    # do ten and stop
    make label ARGS="--status"      # how far through the queue you are

**It is blind by construction, not by discipline.** This tool has no code path that can
reach a classifier prediction: it reads the span trees and the draw, and it does not import
`rlens.classify` at all. That is deliberate and it is the plan's own instruction — *"build
it blind; a tool that can show predictions will show them the day labelling gets tedious"*.
If a future version needs to display predictions for some other purpose, it must be a
different tool with a different name.

What it shows, and what it withholds
------------------------------------
Shown: the problem, the step's own text, and the steps *before* it in the same trace.
Withheld: the classifier's label, the known answer, whether the model got the item right,
and the rest of the trace after this step.

The last two are the outcome-bias guard (C6) as a property of the tool rather than a line
in a prompt. An annotator who can see that the trace ends in the right answer will label
its steps more kindly, and no instruction reliably prevents that.

Two labels per step in one pass (C5.2), because the alternative is two passes over the same
text weeks apart, and the second pass is the one that never happens.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import textwrap
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))

from rlens.ingest import otel  # noqa: E402
from rlens.runner.run import load_item  # noqa: E402
from rlens.segment import segment  # noqa: E402

SPANS = ROOT / "out/spans"
SAMPLING = ROOT / "calibration/sampling.json"
LABELS = ROOT / "calibration/labels"
RUBRIC = ROOT / "calibration/rubric.md"

BEHAVIORS = {
    "1": "verification",
    "2": "backtracking",
    "3": "subgoal_setting",
    "4": "backward_chaining",
    "5": "linear",
}
SOUNDNESS = {"1": "sound", "2": "unsound", "3": "unverifiable"}

WIDTH = 88


def _rule(char: str = "-") -> str:
    return char * WIDTH


def _wrap(text: str, indent: str = "") -> str:
    return "\n".join(
        textwrap.fill(line, WIDTH, initial_indent=indent, subsequent_indent=indent) or indent
        for line in text.splitlines() or [""]
    )


def load_traces() -> dict[str, dict[str, object]]:
    """Every step in the corpus, keyed by `step_id`, with its trace context."""
    index: dict[str, dict[str, object]] = {}
    for path in sorted(SPANS.glob("*.json")):
        trace = segment(otel.parse(json.loads(path.read_text())))
        for position, step in enumerate(trace.steps):
            index[step.step_id] = {
                "step": step,
                "item_id": trace.item_id,
                "strategy": trace.strategy,
                "position": position,
                "preceding": trace.steps[:position],
            }
    return index


# C5.1's frame splits the random-90 at 40: positions 1-40 are M1-11's dev pass, 41-90 are
# M2-1a's held-out set. They are different tasks, different files and different weeks, and
# the boundary is the C5.4 overfitting control -- so it is a CLI choice here, never a step
# the queue walks over on its own.
PARTS = {
    "dev": ("draw", 0, 40, "dev-100.jsonl"),
    "heldout": ("draw", 40, None, "heldout-50.jsonl"),
    "enriched": ("enriched", 0, None, "dev-100.jsonl"),
}


def labels_path(part: str) -> pathlib.Path:
    return LABELS / PARTS[part][3]


def already_labelled(annotator: str) -> set[str]:
    """Every step this annotator has labelled, in whichever file it landed in.

    Scans the whole directory rather than one file. Reading only `<annotator>.jsonl` meant
    that splitting the labels into the dev and held-out files the plan names lost the
    tool's memory of the pass and re-served all 90 steps as unlabelled.
    """
    done: set[str] = set()
    if not LABELS.is_dir():
        return done
    for path in sorted(LABELS.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("annotator", path.stem) == annotator:
                done.add(row["step_id"])
    return done


def render(entry: dict[str, object], item: dict[str, object], n: int, total: int) -> str:
    step = entry["step"]
    out = [
        "",
        _rule("="),
        f"  STEP {n} of {total}   ·   {entry['strategy']} arm   ·   "
        f"step {int(entry['position']) + 1} of this trace",
        _rule("="),
        "",
        "  PROBLEM",
        _wrap(str(item["prompt"]), "    "),
        "",
    ]
    preceding = entry["preceding"]
    if preceding:
        out.append(f"  THE {len(preceding)} STEP(S) BEFORE THIS ONE (context — do not label these)")
        for i, prev in enumerate(preceding):  # type: ignore[call-overload]
            body = prev.text.strip().replace("\n", " ")
            if len(body) > 400:
                body = body[:400] + " …"
            out.append(_wrap(f"[{i + 1}] {body}", "    "))
        out.append("")
    else:
        out.append("  (this is the first step of the trace)")
        out.append("")
    out += [
        _rule(),
        f"  THE STEP YOU ARE LABELLING   ·   kind: {step.kind}",  # type: ignore[union-attr]
        _rule(),
        _wrap(str(step.text).strip() or "(empty)", "    "),  # type: ignore[union-attr]
        "",
    ]
    return "\n".join(out)


def prompt_choice(title: str, options: dict[str, str]) -> str | None:
    """Returns the chosen value, or None to skip. Re-asks rather than accepting a guess."""
    menu = "   ".join(f"[{k}] {v}" for k, v in options.items())
    while True:
        print(f"  {title}")
        print(f"    {menu}      [s] skip   [q] quit")
        raw = input("  > ").strip().lower()
        if raw in ("q", "quit"):
            raise KeyboardInterrupt
        if raw in ("s", "skip"):
            return None
        if raw in options:
            return options[raw]
        # Also accept the label spelled out, because a careful annotator will type it.
        for value in options.values():
            if raw == value:
                return value
        print("  ? not one of the options\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotator", default=os.environ.get("ANNOTATOR", ""), help="your name")
    ap.add_argument("--count", type=int, default=0, help="stop after this many (0 = no limit)")
    ap.add_argument("--status", action="store_true", help="show progress and exit")
    # Exists because smoke-testing this tool without it writes a fake label into
    # calibration/labels/, where everything downstream treats a row as ground truth. A
    # deleted fake is fine; an undeleted one is a label nobody wrote being counted as one.
    ap.add_argument("--dry-run", action="store_true", help="render and prompt, write nothing")
    # See PARTS. `dev` is the default because the parts are labelled in a fixed order and
    # `dev` is first: starting on `enriched` would put the easiest-to-find rare classes
    # into the dev set before the number that has to be independent exists, and starting on
    # `heldout` would label the published-kappa set before the dev set it is held out from.
    ap.add_argument(
        "--part",
        choices=tuple(PARTS),
        default="dev",
        help="which part of the sampling frame to serve (default: dev = random 1-40)",
    )
    args = ap.parse_args(argv)

    source, start, stop, _ = PARTS[args.part]
    record = json.loads(SAMPLING.read_text())
    draw = record.get(source, {})
    queue: list[str] = (draw.get("ordered_step_ids") or [])[start:stop]
    if not queue:
        target = "make draw-sample" if source == "draw" else "make draw-enriched"
        print(
            f"no {args.part} draw in calibration/sampling.json. Run `{target}` first -- the "
            f"seed and the ordered id list are committed BEFORE the first label (Hazard 2).",
            file=sys.stderr,
        )
        return 2

    if not args.annotator:
        print(
            "--annotator is required (or set ANNOTATOR). It is recorded on every label.",
            file=sys.stderr,
        )
        return 2
    annotator = args.annotator.strip().lower().replace(" ", "-")

    # Scoped to this part, or the count reads against the wrong denominator: the annotator
    # who has finished dev and held-out has 90 labels and a 40-step queue.
    done = already_labelled(annotator) & set(queue)
    remaining = [sid for sid in queue if sid not in done]
    if args.status:
        print(
            f"annotator {annotator}: {len(done)} of {len(queue)} labelled in --part "
            f"{args.part}, {len(remaining)} to go"
        )
        print(
            f"  seed {draw.get('seed')} · drawn {draw.get('drawn_utc')} · {labels_path(args.part)}"
        )
        return 0

    if not remaining:
        print(f"nothing left in the queue for {annotator} ({len(done)} of {len(queue)} done)")
        return 0

    index = load_traces()
    missing = [sid for sid in remaining if sid not in index]
    if missing:
        # A drawn step that no longer exists means the segmenter moved under the draw.
        # That is Hazard 1 firing, and it must stop the pass rather than skip the step.
        print(
            f"{len(missing)} drawn step(s) are not in the corpus, e.g. {missing[:3]}. "
            f"The segmenter has changed since the draw was taken "
            f"({record['segmenter_freeze']['tag']}), so every ordinal has moved and these "
            f"labels would attach to different text. Stop and resolve the freeze.",
            file=sys.stderr,
        )
        return 2

    print(f"\n  Rubric: {RUBRIC.relative_to(ROOT)}  ·  read it before you start, and keep it open.")
    print(f"  Annotator: {annotator}  ·  {len(done)} done, {len(remaining)} remaining\n")

    LABELS.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        for sid in remaining:
            if args.count and written >= args.count:
                break
            entry = index[sid]
            item = load_item(str(entry["item_id"]))
            print(render(entry, item, len(done) + written + 1, len(queue)))

            behavior = prompt_choice("BEHAVIOR", BEHAVIORS)
            soundness = prompt_choice("SOUNDNESS", SOUNDNESS) if behavior else None
            note = input("  notes (optional, enter to skip)\n  > ").strip()

            row = {
                "step_id": sid,
                "item_id": entry["item_id"],
                "strategy": entry["strategy"],
                "text": entry["step"].text,  # type: ignore[union-attr]
                "behavior_label": behavior,
                "soundness_label": soundness,
                "annotator": annotator,
                "labeled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "rubric_version": "v1",
            }
            if note:
                row["notes"] = note
            if behavior is None:
                # A skip is DATA -- it says the rubric could not decide this step -- so it
                # is written down rather than silently leaving a gap in the queue.
                row["skipped"] = True
            if args.dry_run:
                print(f"  DRY RUN -- not written: {json.dumps(row)[:120]}...\n")
            else:
                with labels_path(args.part).open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(f"  recorded{' (skipped)' if behavior is None else ''}\n")
            written += 1
    except (KeyboardInterrupt, EOFError):
        print("\n  stopped. Everything labelled so far is already written.\n")

    if args.dry_run:
        print(f"  {written} this session, DRY RUN -- nothing written\n")
        return 0
    total = len(already_labelled(annotator))
    print(f"  {written} this session · {total} of {len(queue)} in {labels_path(args.part)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
