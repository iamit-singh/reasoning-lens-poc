"""Live re-runs and their progress stream — G3 **E2**, the half ADR-003 did not delete.

Owner: M3-1b.

E2 asks for *"live re-run end to end, SSE, every degraded branch reachable"*. It was
recorded as **deleted scope** because C10.4 wrote it against a hosted service and
[ADR-003](../docs/decisions/ADR-003-hosting.md) deleted the hosting. That reasoning covered
the *deployment* and was then applied one step too far: **the backend still runs**, one
process on a laptop serving one origin (FE-9), and `POST /api/runs` has existed since
M3-1a. There has always been a process to stream from. What was missing was that the route
returned `202` and then did nothing at all.

So this is the deleted half rebuilt against what actually exists, and nothing here needs a
host, a queue, a worker pool or a second machine.

What this does not change
-------------------------
**The shipping demo is unaffected.** `DEMO_MODE=cached` refuses live runs with `503` before
any of this is reached, and that is still the demo-safety switch C9 specifies. The cached
read path keeps its guarantee that a `GET` never triggers a model call (C4.9, B4 #8) —
generation happens only behind an explicit `POST`, and the progress stream is a separate
`GET` that reads an in-memory queue and calls nothing.

**The input surface is unchanged.** A run request is `{"item_id": "..."}` validated against
the static allowlist, exactly as before. Nothing here accepts free text, and the stream is
addressed by a server-minted run id.

Why the registry is a dict
--------------------------
[ADR-011](../docs/decisions/ADR-011-no-redis.md): one process, one operator. A shared run
registry is coordination between replicas that do not exist, and Redis cannot make this
demo more reliable while it can certainly make it less, by being down. Runs are held in
memory, bounded, and lost on restart — which is correct for a demo whose durable artifacts
are the cached reports on disk.

The spend problem, stated plainly because it is a real gap
----------------------------------------------------------
`breaker.record()` exists, is tested, and **was called from nowhere in production** — which
was harmless while nothing spent money, and stops being harmless the moment this file
exists. The obvious repair is to record dollars after each run. **It cannot be done
honestly**: `analyzer/prices.json` carries `null` rates for every analysis model on purpose,
because nobody has verified the per-token prices and *"an invented rate would make
`est_cost_usd` look measured when it was assumed"*.

So the dollar breaker is still checked — it catches a manual trip and a recorded balance —
and it is **supplemented, not replaced**, by a budget in a unit that is actually measurable:

* **analysis calls**, counted per run and per process. A call is a countable event; a dollar
  here is a guess. `LIVE_RUN_CALL_BUDGET` refuses the run that would exceed it.

The run's measured token counts are reported back on the stream, so an operator sees what
was spent in the unit this project can defend. **A dollar figure is deliberately absent
rather than estimated**, and `/readyz` says so instead of implying the breaker is watching
something it cannot see.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import os
import pathlib
import tempfile
import time
from collections import OrderedDict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Analysis calls one run may make. Three arms, one classify call each, plus headroom for
#: the triage pass -- a run that wants more than this is not the run this route offers.
LIVE_RUN_CALL_BUDGET = int(os.environ.get("LIVE_RUN_CALL_BUDGET", "8"))

#: Analysis calls this PROCESS may make across all live runs before refusing. The per-run
#: budget bounds one mistake; this bounds a loop of them, which is the failure the spend
#: breaker would have caught if it could see dollars.
LIVE_PROCESS_CALL_BUDGET = int(os.environ.get("LIVE_PROCESS_CALL_BUDGET", "60"))

#: Runs kept in memory. Bounded so a long-lived demo cannot grow without limit.
MAX_RUNS = 32

#: The stage sequence, in order. Published so the UI renders the whole ladder up front
#: rather than growing a list as events arrive -- a reader who can see what is still to
#: come can tell "slow" from "stuck", and a progress display that cannot is a spinner.
STAGES: tuple[str, ...] = ("accepted", "generating", "segmenting", "classifying", "assembling")


@dataclasses.dataclass(slots=True)
class Event:
    """One progress event. `seq` is monotonic per run so a late subscriber can order them."""

    seq: int
    stage: str
    status: str  # started | ok | degraded | failed | budget
    detail: str
    at: float

    def sse(self) -> str:
        payload = json.dumps(dataclasses.asdict(self), sort_keys=True)
        return f"event: progress\ndata: {payload}\n\n"


@dataclasses.dataclass
class Run:
    run_id: str
    item_id: str
    created_at: float
    events: list[Event] = dataclasses.field(default_factory=list)
    status: str = "running"  # running | done | failed
    report: dict[str, Any] | None = None
    error: str | None = None
    calls: int = 0
    tokens: dict[str, int] = dataclasses.field(default_factory=dict)
    _queues: list[asyncio.Queue] = dataclasses.field(default_factory=list, repr=False)

    def public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "item_id": self.item_id,
            "status": self.status,
            "stages": list(STAGES),
            # The report itself is NOT inlined here: this payload is polled, and a reader
            # wanting the object asks for it once at `/api/runs/{id}/report`, where it
            # carries its `live: true` provenance flag.
            "report_available": self.report is not None,
            "events": [dataclasses.asdict(e) for e in self.events],
            "error": self.error,
            "analysis_calls": self.calls,
            "tokens": self.tokens,
            # Named so nobody reads the absence as "it was free". See the module docstring.
            "est_cost_usd": None,
            "cost_note": "not priced -- analyzer/prices.json carries null rates deliberately",
        }


_RUNS: OrderedDict[str, Run] = OrderedDict()
_PROCESS_CALLS = 0


def process_calls() -> int:
    return _PROCESS_CALLS


def budget_state() -> dict[str, Any]:
    """What `/readyz` should say about the thing the dollar breaker cannot see."""
    return {
        "analysis_calls_used": _PROCESS_CALLS,
        "analysis_calls_limit": LIVE_PROCESS_CALL_BUDGET,
        "per_run_limit": LIVE_RUN_CALL_BUDGET,
        "note": "calls, not dollars -- prices.json is deliberately unpriced",
    }


def get(run_id: str) -> Run | None:
    return _RUNS.get(run_id)


def reset_for_tests() -> None:
    global _PROCESS_CALLS
    _RUNS.clear()
    _PROCESS_CALLS = 0


def _emit(run: Run, stage: str, status: str, detail: str = "") -> None:
    ev = Event(seq=len(run.events), stage=stage, status=status, detail=detail, at=time.time())
    run.events.append(ev)
    for q in list(run._queues):
        with contextlib.suppress(asyncio.QueueFull):
            q.put_nowait(ev)


async def subscribe(run: Run) -> Any:
    """Yield SSE frames for `run`: **every event from the beginning**, then live ones.

    **Replay from seq 0 is the point, not a nicety.** A subscriber that only saw events
    arriving after it connected would show a different story depending on how fast the
    reader clicked -- and the first stages are the fast ones, so the common case is a
    viewer who opens the stream and sees it start at "classifying" with no idea the earlier
    stages happened at all. E2 asks for the sequence to be reachable; a sequence you can
    only catch by being early is not.

    The stream always ends with a terminal `end` frame and then closes, so a client never
    waits on a run that finished before it subscribed.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    seen = 0
    # Replay under the same lock-free assumption the rest of this module makes: one event
    # loop, one process. Events already in the list are replayed; anything appended after
    # this point also lands in `q`, so the `seen` guard below drops the overlap.
    run._queues.append(q)
    try:
        for ev in list(run.events):
            seen = max(seen, ev.seq + 1)
            yield ev.sse()
        while run.status == "running" or not q.empty():
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.5)
            except TimeoutError:
                # A heartbeat, so a proxy or a sleeping tab does not silently drop an
                # idle stream during a two-minute generation.
                yield ": keep-alive\n\n"
                continue
            if ev.seq < seen:
                continue
            seen = ev.seq + 1
            yield ev.sse()
        terminal = {
            "run_id": run.run_id,
            "status": run.status,
            "error": run.error,
            "analysis_calls": run.calls,
            "tokens": run.tokens,
            "est_cost_usd": None,
        }
        yield f"event: end\ndata: {json.dumps(terminal, sort_keys=True)}\n\n"
    finally:
        with contextlib.suppress(ValueError):
            run._queues.remove(q)


def start(item: dict[str, Any]) -> Run:
    """Register a run and schedule it. Returns immediately; the work happens in the loop."""
    run_id = f"run-{int(time.time() * 1000):x}"
    run = Run(run_id=run_id, item_id=item["id"], created_at=time.time())
    _RUNS[run_id] = run
    while len(_RUNS) > MAX_RUNS:
        _RUNS.popitem(last=False)
    _emit(run, "accepted", "ok", f"queued {item['id']}")
    asyncio.get_event_loop().create_task(_execute(run, item))
    return run


async def _execute(run: Run, item: dict[str, Any]) -> None:
    """Generate, segment, classify, assemble — emitting a stage event at each boundary.

    **Every failure below is a degraded branch that still produces a report**, which is what
    E2's "every degraded branch reachable" asks for. An arm that fails to generate is
    reported as a failed arm and the other two render; an analysis call that fails leaves a
    degraded arm with its reason attached. The only outcome that produces no report is one
    where nothing generated at all, and that is reported as a failed run rather than as an
    empty success.
    """
    global _PROCESS_CALLS
    # Imported lazily and narrowly: the analyzer is a heavy import, and `make backend-tests`
    # exercises the cached read path, which must not pay for it.
    from rlens.pipeline import analyze_item
    from rlens.runner.arms import ARMS
    from rlens.runner.run import run_arms

    strategies = sorted(ARMS)
    budget = min(LIVE_RUN_CALL_BUDGET, LIVE_PROCESS_CALL_BUDGET - _PROCESS_CALLS)
    if budget < len(strategies):
        run.status = "failed"
        run.error = (
            f"analysis call budget exhausted ({_PROCESS_CALLS}/{LIVE_PROCESS_CALL_BUDGET} "
            "used this process). This is the guard that stands in for a dollar breaker the "
            "price table cannot feed."
        )
        _emit(run, "accepted", "budget", run.error)
        return

    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"rlens-{run.run_id}-"))
    try:
        # ---------------------------------------------------------------- generate
        _emit(run, "generating", "started", f"{len(strategies)} arms, local model")
        try:
            results = await run_arms(item["id"], item["prompt"], strategies)
        except Exception as exc:
            run.status = "failed"
            run.error = f"generation failed: {type(exc).__name__}: {str(exc)[:300]}"
            _emit(run, "generating", "failed", run.error)
            return

        # **The span envelope is `{"resourceSpans": [...]}`, exactly as `python -m
        # rlens.runner` writes it.** Not a detail: `analyze_item` reads these files with the
        # same `otel.parse` the offline pipeline uses, so a live run and `make report` have
        # to produce byte-compatible input or the live path is quietly a second pipeline
        # that happens to look like the first.
        wrote = 0
        for res in results:
            if res.spans:
                path = tmp / f"{item['id']}.{res.strategy}.json"
                path.write_text(json.dumps({"resourceSpans": res.spans}, sort_keys=True))
                wrote += 1
                if res.ok:
                    _emit(run, "generating", "ok", f"{res.strategy}: {res.trace_quality}")
                else:
                    # A FAILED ARM IS STILL WRITTEN, and that is the degraded branch E2
                    # names. Its span tree records the failure, so `build_arm` renders it
                    # as a failed column beside two good ones (C4.1/B6.5) instead of the
                    # arm silently vanishing from the report.
                    _emit(
                        run,
                        "generating",
                        "degraded",
                        f"{res.strategy}: {(res.failed_reason or 'failed')[:200]}",
                    )
            else:
                _emit(
                    run,
                    "generating",
                    "degraded",
                    f"{res.strategy}: no spans ({(res.failed_reason or 'unknown')[:160]})",
                )
        if not wrote:
            run.status = "failed"
            run.error = "no arm produced a trace; there is nothing to analyse"
            _emit(run, "generating", "failed", run.error)
            return

        # ---------------------------------------------------------------- segment+classify
        _emit(run, "segmenting", "started", f"{wrote} traces")
        _emit(run, "classifying", "started", f"{wrote} analysis calls, budget {budget}")
        loop = asyncio.get_event_loop()
        try:
            report = await loop.run_in_executor(None, lambda: analyze_item(item, tmp))
        except Exception as exc:
            run.status = "failed"
            run.error = f"analysis failed: {type(exc).__name__}: {str(exc)[:300]}"
            _emit(run, "classifying", "failed", run.error)
            return
        finally:
            run.calls += wrote
            _PROCESS_CALLS += wrote

        for arm in report.get("arms", []):
            if arm.get("degraded"):
                _emit(
                    run,
                    "classifying",
                    "degraded",
                    f"{arm['strategy']}: {arm['degraded'].get('reason')}",
                )
            else:
                _emit(run, "classifying", "ok", f"{arm['strategy']}: classified")

        # ---------------------------------------------------------------- assemble
        _emit(run, "assembling", "started", "validating against the committed schema")
        run.tokens = _tokens(report)
        run.report = report
        run.status = "done"
        _emit(run, "assembling", "ok", f"{len(report.get('arms', []))} arms")
    except Exception as exc:  # a bug here must not leave a stream open forever
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {str(exc)[:300]}"
        _emit(run, "assembling", "failed", run.error)
    finally:
        if run.status == "running":
            run.status = "failed"
            run.error = run.error or "run ended without a terminal state"
        for q in list(run._queues):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(Event(len(run.events), "assembling", run.status, "", time.time()))


def _tokens(report: dict[str, Any]) -> dict[str, int]:
    """Measured token counts, summed across arms. The unit this project can defend."""
    out = {"reasoning": 0, "output": 0, "input": 0}
    for arm in report.get("arms", []):
        m = arm.get("metrics") or {}
        out["reasoning"] += int(m.get("reasoning_tokens") or 0)
        out["output"] += int(m.get("output_tokens") or 0)
        out["input"] += int(m.get("input_tokens") or 0)
    return out
