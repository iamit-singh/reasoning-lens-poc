"""``python -m rlens`` — span trees in, a `ReasoningReport` out.

    python -m rlens --item mb-08                 # from out/spans, report to out/reports
    python -m rlens --item mb-08 --stdout        # the report on stdout
    MOCK_LLM=1 python -m rlens --all             # the whole bank, offline, from cassettes

Owner: M1-10. This is the last third of the chain; the first two have been reachable since
W3 (`python -m rlens.runner` writes the span trees, `segment` turns one into steps).

**It reads span trees rather than producing them, and that is I1, not a convenience.** The
analyzer's only input is a span tree — it never calls a generation model, and a third-party
tree from a stock LangGraph agent enters here on exactly the same footing as one of ours.
Generation is `python -m rlens.runner`, and the two stay separate commands so that
separation is visible rather than asserted.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from rlens.llm import ProviderError
from rlens.pipeline import analyze_item
from rlens.runner.paths import data_path
from rlens.runner.run import load_item


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rlens", description=__doc__)
    ap.add_argument("--item", help="bank item id, e.g. mb-08")
    ap.add_argument("--all", action="store_true", help="every item with a span tree")
    ap.add_argument("--spans", default="out/spans", help="directory of span trees")
    ap.add_argument("--out", default="out/reports", help="where reports are written")
    ap.add_argument("--stdout", action="store_true", help="print the report instead of writing it")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not args.item and not args.all:
        ap.error("one of --item or --all is required")

    spans = pathlib.Path(args.spans)
    if not spans.is_dir():
        sys.stderr.write(
            f"no span trees at {spans}. Generate them with "
            f"`python -m rlens.runner --item <id> --all-arms`, or replay the committed "
            f"cassettes with `make spans`.\n"
        )
        return 2

    if args.all:
        item_ids = sorted({p.name.split(".")[0] for p in spans.glob("*.json")})
    else:
        item_ids = [args.item]

    outdir = pathlib.Path(args.out)
    if not args.stdout:
        outdir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for item_id in item_ids:
        try:
            item = load_item(item_id)
        except FileNotFoundError:
            # A span tree whose item is gone is a broken pairing, not a reason to abandon
            # the other items -- the same rule B6.5 applies to arms, one level up.
            sys.stderr.write(f"{item_id}: no bank item at {data_path('problem-bank/items')}\n")
            failures += 1
            continue
        try:
            report = analyze_item(item, spans)
        except (ProviderError, FileNotFoundError) as exc:
            sys.stderr.write(f"{item_id}: {type(exc).__name__}: {exc}\n")
            failures += 1
            continue

        body = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.stdout:
            sys.stdout.write(body)
        else:
            path = outdir / f"{item_id}.report.json"
            path.write_text(body)
            arms = ", ".join(
                f"{arm['strategy']}"
                + ("*" if arm.get("degraded") else "")
                + ("!" if arm["status"] == "failed" else "")
                for arm in report["arms"]
            )
            print(f"{path}  [{arms}]")

    if failures:
        sys.stderr.write(f"\n{failures} of {len(item_ids)} items did not produce a report\n")
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
