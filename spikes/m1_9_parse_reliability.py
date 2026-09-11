#!/usr/bin/env python3
"""M1-9's DoD, measured: a valid row for every step across the bank x 3 arms, with a
parse-failure rate under 2% over 20 consecutive runs.

Run with ``make classify-reliability ARGS="--runs 20"``.

What counts as a failure, and why the denominator is the *call*
--------------------------------------------------------------
C4.3's robustness rule operates per request: validate -> one repair retry -> degrade. So
the natural unit of "parse failure" is the request, and this harness counts three things
separately rather than folding them together:

* **repaired** -- the first attempt was rejected and the repair retry succeeded. The rows
  are real and the report is complete. This is *not* a parse failure; it is the mechanism
  C4.3 specifies working as designed. It is reported anyway, because a rising repair rate
  is the leading indicator of a rising failure rate.
* **failed** -- both attempts were rejected. The strategy degrades and renders
  unannotated. **This is the DoD's numerator.**
* **hard errors** -- a truncation or an empty response. S3 established these are config
  faults, not competence faults: retrying reproduces them exactly. They are counted and
  named separately, because folding a misconfigured output cap into a "parse-failure
  rate" would report a number that improves when you fix the wrong thing.

A run is one full pass over every committed span tree. Twenty of them is the DoD's
"20 consecutive runs" read literally, which is the only reading that does not quietly
shrink the test.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))

from rlens.classify import ClassificationResult, classify
from rlens.ingest import otel
from rlens.llm import AnalysisTruncated, ProviderError
from rlens.runner.run import load_item
from rlens.segment import segment
from rlens.versions import PROMPT_BUNDLE_VERSION

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPANS = ROOT / "out/spans"
OUT = ROOT / "docs/spikes/M1-9-raw"


@dataclass
class TraceOutcome:
    trace: str
    steps: int
    chunks: int = 0
    repairs: int = 0
    calls: int = 0
    ok: bool = False
    hard_error: str | None = None
    detail: str = ""
    completion_tokens: int = 0
    prompt_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    behaviors: dict[str, int] = field(default_factory=dict)
    verdicts: dict[str, int] = field(default_factory=dict)
    confidence_pairs_identical: int = 0
    rows: int = 0
    call_ms: list[int] = field(default_factory=list)


def _classify_one(path: pathlib.Path) -> TraceOutcome:
    name = path.name.removesuffix(".json")
    item_id = name.split(".")[0]
    tree = json.loads(path.read_text())
    trace = segment(otel.parse(tree))
    out = TraceOutcome(trace=name, steps=len(trace.steps))
    if not trace.steps:
        out.ok = True
        out.detail = "no steps"
        return out
    item = load_item(item_id)
    try:
        res: ClassificationResult = classify(trace, item_prompt=item["prompt"])
    except AnalysisTruncated as exc:
        out.hard_error = "truncated"
        out.detail = str(exc)[:300]
        return out
    except ProviderError as exc:
        out.hard_error = "provider"
        out.detail = str(exc)[:300]
        return out

    out.chunks, out.repairs, out.calls = res.chunks, res.repairs, res.calls
    out.completion_tokens = res.completion_tokens
    out.prompt_tokens = res.prompt_tokens
    out.reasoning_tokens = res.reasoning_tokens
    out.latency_ms = res.latency_ms
    out.call_ms = list(res.call_ms)
    out.ok = res.ok
    out.rows = len(res.rows)
    if res.degraded:
        out.detail = str(res.degraded.get("detail", ""))[:300]
    else:
        out.behaviors = dict(Counter(r.behavior for r in res.rows))
        out.verdicts = dict(Counter(r.verdict for r in res.rows))
        out.confidence_pairs_identical = sum(
            1 for r in res.rows if r.behavior_confidence == r.validity_confidence
        )
    return out


def one_run(paths: list[pathlib.Path], workers: int) -> list[TraceOutcome]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_classify_one, paths))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=1, help="consecutive full passes (DoD: 20)")
    ap.add_argument("--workers", type=int, default=6, help="concurrent traces per run")
    ap.add_argument("--only", default="", help="substring filter on the trace name")
    ap.add_argument("--limit", type=int, default=0, help="cap traces per run (smoke runs)")
    args = ap.parse_args(argv)

    if not SPANS.exists():
        print(f"no span trees at {SPANS}. Run `make spans` first.", file=sys.stderr)
        return 2
    paths = sorted(p for p in SPANS.glob("*.json") if args.only in p.name)
    if args.limit:
        paths = paths[: args.limit]
    if not paths:
        print("no traces matched", file=sys.stderr)
        return 2

    backend = os.environ.get("ANALYZER_BACKEND", "hybrid")
    model = os.environ.get("MODEL_ANALYZE" if backend == "hybrid" else "LOCAL_MODEL", "")
    chunk = os.environ.get("CLASSIFY_CHUNK_SIZE", "25")
    print(
        f"M1-9 parse reliability: {len(paths)} traces x {args.runs} runs, "
        f"backend={backend} model={model} chunk={chunk} bundle={PROMPT_BUNDLE_VERSION}"
    )

    runs: list[list[TraceOutcome]] = []
    started = time.time()
    for i in range(args.runs):
        t = time.time()
        outcomes = one_run(paths, args.workers)
        runs.append(outcomes)
        calls = sum(o.calls for o in outcomes)
        failed = sum(1 for o in outcomes if not o.ok and not o.hard_error)
        hard = sum(1 for o in outcomes if o.hard_error)
        repaired = sum(o.repairs for o in outcomes)
        print(
            f"  run {i + 1:2d}/{args.runs}: {calls:4d} calls, {repaired} repaired, "
            f"{failed} degraded, {hard} hard errors  [{time.time() - t:.0f}s]"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    # **A partial run must not overwrite the full run's record.** S1 had this same defect
    # -- `--only openai` rewrote a results file containing both probes -- and there it cost
    # nothing because the raw output is gitignored and the write-up is the evidence. Here
    # the JSON record IS the evidence for a DoD, so the scope of a run is part of its name.
    scope = (
        "full" if not args.only and not args.limit else f"{args.only or 'all'}-{args.limit or 'n'}"
    )
    record = OUT / f"m1-9-reliability.{scope}.json"
    payload = {
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": backend,
        "model": model,
        "chunk_size": chunk,
        "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
        "scope": {"only": args.only, "limit": args.limit, "workers": args.workers},
        "runs": [[vars(o) for o in run] for run in runs],
    }
    record.write_text(json.dumps(payload, indent=2) + "\n")

    flat = [o for run in runs for o in run]
    calls = sum(o.calls for o in flat)
    repaired = sum(o.repairs for o in flat)
    degraded = [o for o in flat if not o.ok and not o.hard_error]
    hard = [o for o in flat if o.hard_error]
    graded = [o for o in flat if o.steps]
    rate = 100.0 * len(degraded) / calls if calls else 0.0

    print(f"\n{'=' * 78}\nM1-9 DoD\n{'=' * 78}")
    print(
        f"  traces classified        {len(graded)} of {len(flat)} ({len(flat) - len(graded)} empty)"
    )
    print(f"  calls                    {calls}")
    print(
        f"  repaired (retry worked)  {repaired}  ({100.0 * repaired / calls if calls else 0:.2f}%)"
    )
    print(f"  DEGRADED (parse failure) {len(degraded)}  -> {rate:.2f}%   DoD: < 2.00%")
    print(f"  hard errors              {len(hard)}  ({Counter(o.hard_error for o in hard)})")
    rows = sum(o.rows for o in flat)
    steps = sum(o.steps for o in flat if o.ok)
    print(f"  rows returned            {rows} for {steps} steps in non-degraded traces")
    if graded:
        lat = [o.latency_ms for o in graded if o.latency_ms]
        if lat:
            med, worst = statistics.median(lat) / 1000, max(lat) / 1000
            print(f"  latency per trace        median {med:.1f}s  max {worst:.1f}s")
    pairs = sum(o.confidence_pairs_identical for o in flat)
    pair_pct = 100.0 * pairs / rows if rows else 0.0
    print(f"  identical confidences    {pairs} of {rows} rows ({pair_pct:.1f}%)")
    behaviors: Counter[str] = Counter()
    verdicts: Counter[str] = Counter()
    for o in flat:
        behaviors.update(o.behaviors)
        verdicts.update(o.verdicts)
    print(f"  behavior distribution    {dict(behaviors.most_common())}")
    print(f"  verdict distribution     {dict(verdicts.most_common())}")
    for o in degraded[:5]:
        print(f"    DEGRADED {o.trace}: {o.detail}")
    for o in hard[:5]:
        print(f"    HARD {o.trace} ({o.hard_error}): {o.detail}")
    print(f"\n  wall clock {time.time() - started:.0f}s · record: {record}")
    return 0 if rate < 2.0 and not hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
