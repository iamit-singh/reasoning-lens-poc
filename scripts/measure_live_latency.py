#!/usr/bin/env python3
"""B4 #8's **live** half — end-to-end live re-run latency. Run: `make live-latency`.

Owner: M3-1b / E8.

C11.1 budgets the live re-run at **p90 < 120 s** end to end, and models it at ~91 s. Until
23 Sep this half was recorded as *not applicable*: ADR-003 had deleted the hosted service,
so there was no system to measure. M3-1b built the live path, which **turned a
not-applicable into an unmeasured** — a worse status, honestly arrived at. This closes it.

What is being timed, precisely
------------------------------
**`POST /api/runs` to the terminal `end` frame on the SSE stream.** That is the span a
viewer waits through: fan-out, three arms generating in parallel, segmentation,
classification, assembly. It is measured from the client over loopback, so it includes the
stream's own delivery rather than only the server's bookkeeping.

It does **not** include opening the page, and it is **not** the cached read path — that is
B4 #8's other half, already measured at p90 1.0 ms because C4.9 forbids a `GET` from
triggering a model call.

Why the items vary
------------------
**One item repeated n times measures one item n times.** Finding 13 records exactly this
trap from the other end — a calibration draw that turned out to be *"mostly one repeated
sentence"* — and the arms' cost here is dominated by how much the thinking arm reasons,
which is a property of the problem. So the sample walks distinct bank items and reports
which ones, and a reader can see the spread rather than a single number's confidence.

What this measurement cannot tell you, stated before the number
---------------------------------------------------------------
* **One machine, one operator, no concurrency.** Nobody has put this under load and with one
  operator nobody will. This is a *latency* measurement, not a capacity one.
* **Generation dominates, and it is local.** Most of the wall clock is `gpt-oss:20b` on
  consumer hardware, not anything this service does. On different hardware the number moves
  and the code does not.
* **Warm model.** ollama keeps the model resident; a cold first load is excluded and would
  add tens of seconds. The runbook's P8 says to warm it first, so this measures the state
  the demo is actually given in.
* **It spends.** Three analysis calls per run. The call budget in `backend/runs.py` is what
  stops a measurement loop from becoming an unbounded one.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/b4-8-live-latency.json"


def _post(base: str, item_id: str) -> dict:
    req = urllib.request.Request(
        f"{base}/api/runs",
        data=json.dumps({"item_id": item_id}).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _await_end(base: str, events_url: str, deadline: float) -> dict:
    """Block on the SSE stream until its terminal frame. Returns the `end` payload."""
    with urllib.request.urlopen(f"{base}{events_url}", timeout=deadline) as r:
        event = None
        for raw in r:
            line = raw.decode().rstrip("\n")
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: ") and event == "end":
                return json.loads(line[6:])
    raise RuntimeError("stream closed without an end frame")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=10, help="runs; each spends 3 analysis calls")
    ap.add_argument("--deadline", type=float, default=300.0)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument(
        "--recompute",
        metavar="FILE",
        help="re-derive the summary from a previous run's recorded `runs` and exit. The raw "
        "per-run timings ARE the measurement; the summary over them is arithmetic, and "
        "re-deriving it must never cost another round of spend.",
    )
    args = ap.parse_args(argv)

    if args.recompute:
        prior = json.loads(pathlib.Path(args.recompute).read_text())
        out = _summarise(
            prior["runs"],
            prior.get("n_attempted", len(prior["runs"])),
            prior.get("readyz_at_start", {}),
            prior.get("measured_utc"),
        )
        pathlib.Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        _report(out, args.out)
        return 0

    with urllib.request.urlopen(f"{args.base_url}/readyz", timeout=10) as r:
        ready = json.loads(r.read())
    if not ready.get("live_runs"):
        print(
            "live-latency: live runs are off on that server. B4 #8's live half cannot be "
            "measured against a cached-mode demo.\n"
            "  Start one with: DEMO_MODE=live MOCK_LLM=0 make serve-api",
            file=sys.stderr,
        )
        return 2

    bank = sorted(p.stem for p in (ROOT / "problem-bank/items").glob("*.json"))
    if not bank:
        print("live-latency: no bank items", file=sys.stderr)
        return 2
    # Distinct items, cycling only if n exceeds the bank. See the note on finding 13.
    items = [bank[i % len(bank)] for i in range(args.n)]

    rows: list[dict] = []
    for i, item_id in enumerate(items, 1):
        t0 = time.perf_counter()
        try:
            posted = _post(args.base_url, item_id)
            end = _await_end(args.base_url, posted["events_url"], args.deadline)
            elapsed = time.perf_counter() - t0
        except Exception as exc:
            print(f"  [{i}/{args.n}] {item_id}: FAILED {type(exc).__name__}: {exc}")
            rows.append(
                {"item": item_id, "seconds": None, "status": "error", "error": str(exc)[:200]}
            )
            continue
        rows.append(
            {
                "item": item_id,
                "seconds": round(elapsed, 2),
                "status": end.get("status"),
                "analysis_calls": end.get("analysis_calls"),
                "reasoning_tokens": (end.get("tokens") or {}).get("reasoning"),
            }
        )
        print(
            f"  [{i}/{args.n}] {item_id}: {elapsed:6.1f} s  {end.get('status')}"
            f"  ({(end.get('tokens') or {}).get('reasoning')} reasoning tok)"
        )

    out = _summarise(rows, args.n, ready, None)
    if out is None:
        print("live-latency: no successful run to report", file=sys.stderr)
        return 1
    pathlib.Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    _report(out, args.out)
    return 0


def _summarise(rows: list[dict], attempted: int, ready: dict, when: str | None) -> dict | None:
    ok = [r["seconds"] for r in rows if r["seconds"] is not None and r["status"] == "done"]
    if not ok:
        return None
    ok_sorted = sorted(ok)
    n = len(ok_sorted)
    budget = 120

    def rank(p: float) -> int:
        return max(1, min(n, int(-(-p * n // 1))))

    def pct(p: float) -> float:
        # Nearest-rank. **Not interpolated**: with n this small an interpolated percentile
        # invents a value between two observations and reads as more precise than the
        # sample supports.
        return ok_sorted[rank(p) - 1]

    over = [r for r in rows if r["seconds"] is not None and r["seconds"] > budget]
    worst = max((r for r in rows if r["seconds"] is not None), key=lambda r: r["seconds"])

    return {
        "_README": (
            "B4 #8's LIVE half (C11.1: p90 < 120 s). Written by `make live-latency`. "
            "READ `headline` AND `tail` TOGETHER -- the p90 passes and the tail does not, "
            "and reporting only the first would be the more flattering half of one "
            "measurement. The CACHED half is measured separately and is not in this file."
        ),
        "measured_utc": when or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "budget_seconds_p90": budget,
        "n_attempted": attempted,
        "n_succeeded": n,
        "p50_seconds": pct(0.50),
        "p90_seconds": pct(0.90),
        "max_seconds": ok_sorted[-1],
        "min_seconds": ok_sorted[0],
        "mean_seconds": round(statistics.fmean(ok), 2),
        "stdev_seconds": round(statistics.stdev(ok), 2) if n > 1 else None,
        "p90_meets_budget": pct(0.90) < budget,
        "percentile_method": "nearest-rank, not interpolated",
        # **The p90 at this n is a single observation**, and saying so is the difference
        # between a percentile and a number that looks like one. At n=14 the 90th
        # nearest-rank is the 13th value: move that one run and the headline moves with it.
        "p90_rank": f"{rank(0.90)} of {n}",
        "p90_rests_on_observations": n - rank(0.90) + 1,
        "tail": {
            "runs_over_budget": len(over),
            "over_budget": [{"item": r["item"], "seconds": r["seconds"]} for r in over],
            "worst_item": worst["item"],
            "worst_seconds": worst["seconds"],
            "worst_vs_budget": round(worst["seconds"] / budget, 2),
        },
        "caveats": [
            "THE p90 PASSES AND THE TAIL DOES NOT. Both are the same measurement.",
            "At this n the p90 is ONE observation (see p90_rests_on_observations). Moving "
            "one run moves the headline -- this project has had to correct single-run "
            "inference in writing twice.",
            "One machine, one operator, NO CONCURRENCY. This is latency, not capacity.",
            "Generation dominates and it is LOCAL: most of the wall clock is gpt-oss:20b on "
            "consumer hardware, not this service. Different hardware moves the number "
            "without the code changing.",
            "Model warm. A cold ollama load is excluded and would add tens of seconds.",
            "Distinct bank items, not one repeated -- the thinking arm's cost is a property "
            "of the problem (see finding 13 for the same trap from the other end).",
        ],
        "runs": rows,
        "readyz_at_start": ready,
    }


def _report(out: dict, path: str) -> None:
    print(
        f"\nB4 #8 live half: p50 {out['p50_seconds']:.1f} s · p90 {out['p90_seconds']:.1f} s "
        f"(rank {out['p90_rank']}) · max {out['max_seconds']:.1f} s  n={out['n_succeeded']}"
        f"/{out['n_attempted']}, budget {out['budget_seconds_p90']} s"
    )
    t = out["tail"]
    print(
        f"  p90 {'MEETS' if out['p90_meets_budget'] else 'MISSES'} the budget"
        f" -- and {t['runs_over_budget']} run(s) EXCEED it, worst {t['worst_item']} at "
        f"{t['worst_seconds']:.1f} s ({t['worst_vs_budget']}x)."
    )
    print(f"  -> {path}")


if __name__ == "__main__":
    raise SystemExit(main())
