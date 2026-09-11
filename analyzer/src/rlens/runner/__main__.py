"""``python -m rlens.runner`` -- C4.1's DoD entry point.

    python -m rlens.runner --item mb-07 --all-arms

writes one span-tree JSON per arm that passes ``test_span_contract.py``.

Owner: M1-6.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

from rlens.llm import record_cassette
from rlens.runner.arms import ARMS
from rlens.runner.emit import langfuse_status
from rlens.runner.run import check_regime_separation, load_item, run_arms
from rlens.versions import generation_pin


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rlens.runner", description="Strategy Runner (C4.1)")
    ap.add_argument("--item", help="bank item id; reads problem-bank/items/<id>.json")
    ap.add_argument("--prompt", help="run an ad-hoc prompt instead (the bank is M1-4)")
    ap.add_argument("--all-arms", action="store_true", help="every implemented arm")
    ap.add_argument("--arm", action="append", choices=sorted(ARMS), help="repeatable")
    ap.add_argument("--out", default="out/spans", help="directory for the span trees")
    ap.add_argument(
        "--record-cassettes",
        action="store_true",
        help="save each arm's response for MOCK_LLM replay. The full bank x arms "
        "recording job is M1-14 (W4); this is the single-item form the span-contract "
        "test needs so CI can run without a GPU.",
    )
    args = ap.parse_args(argv)

    if not args.item and not args.prompt:
        ap.error("one of --item or --prompt is required")
    strategies = sorted(ARMS) if args.all_arms or not args.arm else args.arm

    item_id = args.item or "adhoc"
    if args.prompt:
        prompt = args.prompt
    else:
        try:
            prompt = load_item(args.item)["prompt"]
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    pin = generation_pin()
    missing = pin.unpinned_fields()
    if missing:
        # Not fatal -- a developer must be able to run before `make pin-local`. But the
        # trees carry an incomplete pin, and a number from an unpinned run is not
        # publishable (C2.3). Saying so here is cheaper than discovering it at G2.
        print(
            f"WARNING: generation pin incomplete, missing {', '.join(missing)}. "
            "Run `make pin-local`. Traces from this run are NOT publishable.",
            file=sys.stderr,
        )
    print(f"langfuse: {langfuse_status()}", file=sys.stderr)

    results = asyncio.run(run_arms(item_id, prompt, strategies, pin=pin))

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for r in results:
        path = outdir / f"{item_id}.{r.strategy}.json"
        path.write_text(json.dumps({"resourceSpans": r.spans}, indent=2, sort_keys=True) + "\n")
        if r.ok:
            c = r.completion
            assert c is not None
            if args.record_cassettes:
                # Arm 3 needs ONE CASSETTE PER TURN, under the same names `run_react`
                # asks for. Recording only the final completion would replay a 3-turn
                # agent as a 1-turn one that somehow already knew the tool results --
                # a green test for a conversation that never happened.
                if r.react is not None:
                    for i, t in enumerate(r.react.turns):
                        name = f"{item_id}.{r.strategy}.t{i}"
                        print(f"  cassette -> {record_cassette(name, t.completion)}")
                else:
                    print(f"  cassette -> {record_cassette(f'{item_id}.{r.strategy}', c)}")
            # Arm 3's cost is the WHOLE loop, not its last turn. Reporting the final
            # completion's count for a 3-turn agent understates it by however much the
            # agent thought before it answered -- which for a ReAct arm is most of it.
            if r.react is not None:
                tokens = sum(t.completion.reasoning_tokens or 0 for t in r.react.turns)
                reasoning = f"{tokens} reasoning tok" if tokens else "no trace"
            else:
                reasoning = (
                    f"{c.reasoning_tokens} reasoning tok" if c.reasoning_tokens else "no trace"
                )
            bound = " BUDGET-BOUND" if c.budget_bound else ""
            extra = ""
            if r.react is not None:
                rr = r.react
                extra = f"  {rr.turn_count}t/{rr.max_turns} {rr.tool_calls_made} calls"
                if rr.failed_tool_calls:
                    extra += f" ({rr.failed_tool_calls} rejected)"
                if rr.max_turns_exhausted:
                    extra += " MAX-TURNS"
            print(f"{r.strategy:<9} {r.trace_quality:<8} {reasoning:<20}{bound}{extra}  -> {path}")
        else:
            failures += 1
            print(f"{r.strategy:<9} FAILED   {r.failed_reason}", file=sys.stderr)

    warning = check_regime_separation(results)
    if warning:
        print(f"\n*** {warning} ***", file=sys.stderr)

    # A run where every arm failed is a failed run. A run where one arm failed is a
    # result with a gap in it, and C4.1 says the others still render -- so it exits 0.
    return 1 if failures == len(results) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
