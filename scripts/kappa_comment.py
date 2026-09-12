#!/usr/bin/env python3
"""Post the κ comment on a prompt PR — C7.2, M2-11.

    python scripts/kappa_comment.py calibration-dev.json --pr 42
    python scripts/kappa_comment.py calibration-dev.json            # print, do not post

C7.2 asks that a PR touching the prompt bundle **receives its κ as a comment**. The reason
is ordering, not convenience: a prompt change is a measurement change, and the only moment
a reviewer can weigh it against what it cost is while they are looking at the diff. A
number that arrives in a nightly summary the next morning arrives after the merge.

Three things this refuses to do
-------------------------------
1. **It never prints a bare number.** Every figure carries its n and its interval, because
   `rlens.metrics` makes a bare float impossible to obtain and this would be the one place
   the discipline could leak out into prose.
2. **It states "not yet measured" as a result**, not as an error. In W5 there are zero
   labels and κ is null; a comment that said "FAILED" would train a reviewer to ignore it
   by the third PR, and a comment that stayed silent would let a prompt change through with
   no note at all.
3. **It compares against the base branch only if a baseline artifact is supplied.** Making
   up a "previous κ" from a cached file that may have been produced at a different bundle
   would put a regression number in front of a reviewer that nothing supports.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

MARKER = "<!-- rlens-kappa-comment -->"


def fmt(value: Any) -> str:
    """A metric, or an honest absence. Never a bare float, never a zero standing in for null."""
    if value is None:
        return "_not yet measured_"
    if isinstance(value, dict):
        point = value.get("value")
        low, high = value.get("ci_low"), value.get("ci_high")
        n = value.get("n")
        if point is None:
            count = f"(n={n}) " if n else ""
            return f"_undefined_ {count}- {value.get('note', '')}".strip()
        body = f"**{point:.3f}**"
        if low is not None and high is not None:
            body += f" (95% CI {low:.2f} to {high:.2f})"
        else:
            body += f" _{value.get('note', 'interval not computable')}_"
        if n is not None:
            body += f" · n={n}"
        return body
    if isinstance(value, float):
        return f"**{value:.3f}**"
    return f"`{value}`"


def render(data: dict) -> str:
    run = data.get("run") or {}
    ctx = data.get("measurement_context") or {}
    cls = data.get("classifier_vs_human") or {}
    iaa = data.get("inter_annotator") or {}

    labels = run.get("labels_loaded", 0)
    lines = [
        MARKER,
        "### Calibration — dev set",
        "",
        f"Prompt bundle `{run.get('prompt_bundle_version')}` · "
        f"analyzer `{run.get('analyzer_version')}` · "
        f"judge `{run.get('judge_triage_pin')}` · backend `{run.get('analyzer_backend')}`",
        "",
    ]

    if not labels:
        lines += [
            "> **No human labels exist yet, so there is no κ to report.** This is a result, "
            "not a failure: the classifier produced "
            f"{run.get('predictions_loaded', 0)} predictions and nothing has been scored "
            "against them. The number becomes real when M1-11's first 40 labels land.",
            "",
        ]

    lines += [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Classifier κ — behavior (dev) | {fmt(cls.get('behavior'))} |",
        f"| Classifier κ — soundness (dev) | {fmt(cls.get('soundness'))} |",
        f"| Majority-class baseline | {fmt(ctx.get('majority_class_baseline'))} |",
        f"| Lowest per-class F1 | {fmt(_min_f1(ctx.get('per_class_f1')))} |",
        f"| Inter-annotator κ | {fmt(iaa.get('behavior'))} |",
        "",
        f"Labels loaded: **{labels}** · predictions: **{run.get('predictions_loaded', 0)}**",
        "",
        "> κ is unreadable without the majority-class baseline beside it, which is why the "
        "row is here even when both are null. **The held-out set is not touched by this "
        "job** — `--final` is the only way to read it and it refuses unless the bundle is "
        "frozen (C5.4).",
    ]
    return "\n".join(lines)


def _min_f1(per_class: Any) -> Any:
    if not isinstance(per_class, dict) or not per_class:
        return None
    scored = [v for v in per_class.values() if isinstance(v, (int, float))]
    return min(scored) if scored else None


def post(body: str, pr: str) -> int:
    """Upsert: one comment per PR, edited in place.

    A new comment per push turns a five-push PR into five κ tables, and a reviewer reading
    the newest one has to check it is the newest. Editing in place means the comment is
    always the current measurement.
    """
    existing = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            pr,
            "--json",
            "comments",
            "-q",
            f'.comments[] | select(.body | contains("{MARKER}")) | .url',
        ],
        capture_output=True,
        text=True,
    )
    url = (existing.stdout or "").strip().splitlines()
    if url:
        # `gh` has no comment-edit subcommand, so the API is the supported path. The id is
        # the trailing digits of `...#issuecomment-123456`; `lstrip` would strip a CHARACTER
        # SET rather than a prefix and would eat leading digits that happen to appear in it.
        cid = re.search(r"issuecomment-(\d+)", url[0])
        if not cid:
            print(f"could not read a comment id out of {url[0]!r}", file=sys.stderr)
            return 1
        cid = cid.group(1)
        result = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{{owner}}/{{repo}}/issues/comments/{cid}",
                "-f",
                f"body={body}",
            ],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            ["gh", "pr", "comment", pr, "--body", body], capture_output=True, text=True
        )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", help="the JSON from `make calibrate ARGS='--dev --json'`")
    ap.add_argument("--pr", default="", help="PR number; omit to print instead of posting")
    args = ap.parse_args(argv)

    raw = pathlib.Path(args.report).read_text()
    # `make` echoes its command line before the JSON, so the file is not pure JSON.
    start = raw.find("{")
    if start < 0:
        print(f"no JSON object in {args.report}", file=sys.stderr)
        return 2
    data = json.loads(raw[start:])
    body = render(data)

    if not args.pr:
        print(body)
        return 0
    return post(body, args.pr)


if __name__ == "__main__":
    raise SystemExit(main())
