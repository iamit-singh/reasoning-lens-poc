"""The backend API — C4.9. Cache-first, allowlisted, and it accepts no free text.

Owner: M3-1.

**The security posture is one sentence and it shapes every route below: the only
visitor-controlled input in the entire surface is an item id validated against a static
allowlist** (B0 Condition #1, B6.4). There is no endpoint that accepts free text, and there
is no code path from an HTTP request to a prompt string a visitor composed. That is not a
mitigation to be tuned; it is a property of the route table, and `test_api.py` asserts it by
enumerating the routes rather than by trusting this paragraph.

Cache-first, and what that actually means
-----------------------------------------
`GET /api/report/{id}` **never triggers a model call.** It serves what is on disk or it
returns 404. The live re-run path is `POST /api/runs`, which is separate, rate-limited and
breaker-checked, and which `DEMO_MODE=cached` disables outright.

The reason is B4 #8's two-sided latency budget: the cached path is promised at p90 under 5
seconds, and a read that could silently become a two-minute generation is not a read with a
latency budget — it is a read with a latency hope.

I1, from the other side
-----------------------
`analyzer/` must not import `backend/`. This module imports the analyzer freely, which is
the allowed direction: the analyzer is a standalone package and this is one of its
consumers. The import-linter contract enforces the direction; nothing here needs to be
careful beyond not adding an edge the other way.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from backend import breaker, cache, runs

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "problem-bank/items"
REPORTS_DIR = ROOT / "out/reports"
CALIBRATION = ROOT / "calibration/results/latest.json"
FAITHFULNESS = ROOT / "faithfulness/panel.json"
SEEDED_DIR = ROOT / "calibration/seeded"
REPLAY_REPORTS = ROOT / "calibration/seeded/reports"
FRONTEND_OUT = ROOT / "frontend/out"

#: Server-minted run ids: `run-` plus the lowercase hex of a millisecond clock.
#: Anchored, bounded, and checked before the id is used for anything at all.
_RUN_ID_RE = re.compile(r"run-[0-9a-f]{1,16}")

#: One message for both refusals. See `_checked_run_id`.
_UNKNOWN_RUN = "unknown run id (runs do not survive a restart)"

#: C9. A visitor cannot raise this and a run cannot lower it.
RATE_LIMIT_PER_MIN = int(os.environ.get("RUNS_PER_MIN", "3"))

app = FastAPI(
    title="Reasoning Lens",
    docs_url=None,  # No interactive docs: it is a form, and forms take input.
    redoc_url=None,
    openapi_url=None,
)


# ------------------------------------------------------------------ the allowlist
def _bank() -> dict[str, dict[str, Any]]:
    """Every bank item, by id. **This is the allowlist**, and it is the filesystem.

    Derived from the committed bank rather than configured separately: two lists that are
    supposed to agree eventually do not, and the failure mode of *this* pair disagreeing is
    an id reaching the runner that nobody vetted.
    """
    items: dict[str, dict[str, Any]] = {}
    if not BANK_DIR.is_dir():
        return items
    for path in sorted(BANK_DIR.glob("*.json")):
        item = json.loads(path.read_text())
        items[item["id"]] = item
    return items


def _checked_id(item_id: str) -> dict[str, Any]:
    """Resolve an id or 404. **Every route that takes an id goes through here.**

    Not a path join anywhere, ever: the id indexes a dict built from the bank, so a
    traversal attempt cannot reach the filesystem even in principle. Rejecting `../` with a
    regex would also work and would be one refactor away from not working.
    """
    item = _bank().get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="unknown item id")
    return item


def _report_path(item_id: str) -> pathlib.Path:
    return REPORTS_DIR / f"{item_id}.report.json"


def demo_mode() -> str:
    return os.environ.get("DEMO_MODE", "cached")


def analysis_ready() -> tuple[bool, str]:
    """Can the ANALYSIS tier actually run? Generation being fine is not the same question.

    **This is the asymmetry ADR-001 created and nothing was checking.** Generation is local,
    so it needs no key and works offline. Classification is OpenAI. A live re-run with no
    `OPENAI_API_KEY` therefore generates three traces perfectly well, spends real local
    compute doing it, and *then* fails — halfway, with a half-built report and nothing
    having warned anybody.

    Found by `make smoke --no-key`, which strips the key and got a **202** back from the
    live route. Every read path was correctly green; the write path promised work it could
    not finish.
    """
    backend = os.environ.get("ANALYZER_BACKEND", "hybrid")
    if backend == "local":
        return True, "local analyzer tier; no key required"
    if not os.environ.get("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY is unset, so a live run could generate but not classify"
    if not os.environ.get("MODEL_ANALYZE"):
        return False, "MODEL_ANALYZE is unset (ADR-001: an exact dated id, never an alias)"
    return True, "ok"


# ------------------------------------------------------------------ rate limit (C9)
_HITS: dict[str, list[float]] = {}

#: Guards the read-check-write in `_rate_limited`. See that function's note on why this is
#: belt-and-braces today and why it is still cheap enough to be worth wearing.
_HITS_LOCK = threading.Lock()


def _rate_limited(key: str) -> bool:
    """A **sliding** 60-second window per client. In-process on purpose.

    ADR-003 deleted the deployment: this runs as one process on one laptop, so a shared
    Redis counter would add a dependency whose only job is coordinating with replicas that
    do not exist. If it ever runs replicated, this is the thing to move — and it will be
    obvious, because the limit will be per-replica.

    **The lock is not currently load-bearing, and it is here anyway.** The body is a
    read-modify-write over shared state, which is a race on its face. It is not reachable
    today only because this function is synchronous, its one caller is an `async def`
    coroutine, and no await sits between the length check and the append — so the event
    loop cannot interleave it. That is an accident of how the route happens to be written,
    it is invisible at the call site, and three ordinary edits remove it (make this async,
    add an await between the two lines, or turn the route into a plain `def`, which
    FastAPI then runs in a threadpool). What it protects is **spend**: every admitted run
    is a live model call. An uncontended lock acquired at most a few times a minute costs
    nothing measurable, so the guarantee is made explicit rather than argued for.
    """
    now = time.time()
    with _HITS_LOCK:
        _prune_locked(now)
        window = [t for t in _HITS.get(key, []) if now - t < 60]
        _HITS[key] = window
        if len(window) >= RATE_LIMIT_PER_MIN:
            return True
        window.append(now)
        return False


def _prune_locked(now: float) -> None:
    """Drop every client with no live hit left in its window. Caller holds `_HITS_LOCK`.

    `_HITS` is keyed by a value taken from the request, and before this nothing ever
    removed an entry — an unbounded dict whose keys are chosen by the caller. On a
    one-operator laptop demo that is a small leak rather than a denial of service, which is
    exactly why it would have survived to wherever this code went next.

    **Staleness, not emptiness.** The obvious version drops keys whose list is empty, and
    that collects nothing: a window is only emptied by `_rate_limited` being called for
    that key again, which is precisely when the key is not garbage. The entries have to be
    aged out here.
    """
    for key in [k for k, hits in _HITS.items() if not any(now - t < 60 for t in hits)]:
        del _HITS[key]


def _prune_rate_limit_keys() -> None:
    """Lock-taking wrapper over :func:`_prune_locked`, for tests and for a caller that
    wants to reclaim without recording a hit."""
    with _HITS_LOCK:
        _prune_locked(time.time())


# ------------------------------------------------------------------ routes
@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, Any]:
    """Readiness, and it reports what it is ready *for*.

    A readiness probe that says "ok" while the cache is empty is a probe that lets a demo
    start with nothing to show. `cached_reports` is the number the operator actually needs
    before walking on stage.
    """
    staleness = cache.scan()
    stale = [s for s in staleness if not s.fresh and s.error is None]
    state = breaker.check()
    # **Stale is `degraded`, not `ok`.** A probe that goes green over reports built by a
    # different pipeline is a probe that lets the demo publish numbers describing a system
    # that is not running (M3-2b, ADR-011).
    return {
        "status": "ok" if (staleness and not stale) else "degraded",
        "demo_mode": demo_mode(),
        "bank_items": len(_bank()),
        "cached_reports": len(staleness),
        "stale_reports": [s.describe() for s in stale],
        "calibration": CALIBRATION.exists(),
        # The operator's pre-flight question is "will a visitor see the site or a JSON
        # 404?", and the answer is import-time state they cannot otherwise inspect: the
        # mount below is resolved once, so a frontend built after the server started is
        # not served until it restarts. Reporting it here makes that checkable from the
        # probe the runbook already tells them to curl (P2).
        "frontend_mounted": any(r.path == "" for r in app.routes if hasattr(r, "path")),
        "live_runs": demo_mode() != "cached" and state.allowed and analysis_ready()[0],
        "analysis_tier": {"ready": analysis_ready()[0], "reason": analysis_ready()[1]},
        # **What the dollar breaker below cannot see.** `analyzer/prices.json` carries null
        # rates on purpose, so no live run can report an honest `est_cost_usd` and
        # `breaker.record()` has nothing truthful to be given. Reporting the call budget
        # beside the breaker keeps the operator from reading `spent_usd: 0.0` as "this ran
        # for free" when it means "nothing here can price it". See `backend/runs.py`.
        "live_run_budget": runs.budget_state(),
        "breaker": {
            "allowed": state.allowed,
            "reason": state.reason,
            "spent_usd": state.spent_usd,
            "limit_usd": state.limit_usd,
        },
    }


@app.get("/api/bank")
def bank() -> dict[str, Any]:
    """Bank items grouped by tag, marking which have a cached report."""
    items = _bank()
    cached = (
        {p.name.split(".")[0] for p in REPORTS_DIR.glob("*.report.json")}
        if REPORTS_DIR.is_dir()
        else set()
    )
    by_tag: dict[str, list[str]] = {}
    for item in items.values():
        for tag in item.get("tags", []):
            by_tag.setdefault(tag, []).append(item["id"])
    return {
        "items": [
            {
                "id": item["id"],
                "prompt": item["prompt"],
                "tags": item.get("tags", []),
                "cached": item["id"] in cached,
            }
            for item in items.values()
        ],
        "by_tag": {tag: sorted(ids) for tag, ids in sorted(by_tag.items())},
    }


@app.get("/api/report/{item_id}")
def report(item_id: str) -> Any:
    """Cache-first. **Never triggers a model call** — see the module docstring."""
    _checked_id(item_id)
    path = _report_path(item_id)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="no cached report for this item. Generate one with `make report`.",
        )
    return json.loads(path.read_text())


@app.get("/api/report/{item_id}/download")
def download(item_id: str) -> Response:
    """The same JSON, as an attachment. The same bytes — not a re-serialisation."""
    _checked_id(item_id)
    path = _report_path(item_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="no cached report for this item")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"{item_id}.report.json",
        headers={"Content-Disposition": f'attachment; filename="{item_id}.report.json"'},
    )


@app.get("/api/calibration")
def calibration() -> Any:
    """`calibration/results/latest.json`, verbatim.

    **Verbatim is the contract, not a shortcut.** FE-6 renders this with zero hard-coded
    numbers, so any reshaping here would be a number on the page that the file does not
    contain — and a grep over the frontend source could not catch it.
    """
    if not CALIBRATION.exists():
        raise HTTPException(
            status_code=503, detail="no calibration results yet; run `make calibrate`"
        )
    return json.loads(CALIBRATION.read_text())


@app.get("/api/faithfulness")
def faithfulness() -> Any:
    if not FAITHFULNESS.exists():
        raise HTTPException(status_code=503, detail="no faithfulness panel yet (M2-9)")
    return json.loads(FAITHFULNESS.read_text())


@app.get("/api/replay/{case_id}")
def replay(case_id: str) -> Any:
    """A seeded-error report, flagged as illustrative.

    `illustrative: true` is in the payload rather than left to the UI: this is a report
    whose errors were **planted**, and it travels to a download, a cache and possibly a
    screenshot. The flag has to be attached to the data, not to the page that happened to
    render it.
    """
    cases = {p.stem: p for p in SEEDED_DIR.glob("*.json")} if SEEDED_DIR.is_dir() else {}
    path = cases.get(case_id)
    if path is None:
        raise HTTPException(status_code=404, detail="unknown replay case")
    payload: dict[str, Any] = {"illustrative": True, "case": json.loads(path.read_text())}
    # M2-6's mutated report, if it has been built. **Served only from here**, never from
    # `/api/report/{id}`: the text this judge saw was deliberately edited, so it is neither
    # an authored fixture nor a clean measurement, and the `illustrative` flag above is the
    # only thing that says so. Routing it through the ordinary report path would strip that
    # distinction at exactly the moment it matters -- a download, a cache, a screenshot.
    built = REPLAY_REPORTS / f"{case_id}.report.json"
    if built.is_file():
        payload["replay"] = json.loads(built.read_text())
    return payload


@app.post("/api/runs")
async def create_run(request: Request) -> JSONResponse:
    """Start a live re-run. Allowlisted, rate-limited, breaker-checked.

    **The body is parsed for exactly one key and every other key is ignored.** A run request
    is `{"item_id": "mb-08"}` and nothing else reaches anything: no prompt, no model, no
    parameters. C4.9's "no endpoint accepts free text" is enforced here, at the only route
    where it could fail.
    """
    if demo_mode() == "cached":
        # C9's demo-safety switch. 503 rather than 403: the capability exists and is
        # deliberately off, which is a different thing from the caller not being allowed.
        raise HTTPException(
            status_code=503,
            detail="live runs are disabled (DEMO_MODE=cached). Cached reports are served normally.",
        )

    # **The breaker is checked before the rate limit, deliberately.** A tripped breaker is
    # a hard stop that no amount of waiting clears, and telling a caller to "try again in a
    # minute" when the answer is "never, until someone resets the budget" wastes their time
    # and hides the real state.
    state = breaker.check()
    if not state.allowed:
        raise HTTPException(status_code=503, detail=state.reason)

    # Refuse up front rather than halfway. See `analysis_ready`.
    ready, why = analysis_ready()
    if not ready:
        raise HTTPException(
            status_code=503,
            detail=f"live runs unavailable: {why}. Cached reports are served normally.",
        )

    client = request.client.host if request.client else "unknown"
    if _rate_limited(client):
        raise HTTPException(status_code=429, detail="too many runs; try again in a minute")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="expected a JSON object") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="expected a JSON object")

    item_id = body.get("item_id")
    if not isinstance(item_id, str):
        raise HTTPException(status_code=400, detail="item_id is required")
    item = _checked_id(item_id)

    run = runs.start(item)
    # **202 with somewhere to look.** The route accepted work that has not happened yet, and
    # a caller holding only an id has to guess the URL of the thing it was given an id for.
    return JSONResponse(
        {
            "run_id": run.run_id,
            "item_id": item_id,
            "status_url": f"/api/runs/{run.run_id}",
            "events_url": f"/api/runs/{run.run_id}/events",
            "stages": list(runs.STAGES),
        },
        status_code=202,
    )


def _checked_run_id(run_id: str) -> Any:
    """Resolve a run id, or 404. **The third place a visitor writes a string.**

    `item_id` and `case_id` are checked against a STATIC allowlist. A run id cannot be:
    it is minted by the server at `POST /api/runs`, so the set is not known until runtime.
    What replaces the static list is a **shape check plus a membership check against a
    registry the visitor cannot add to** — the ids are server-generated, the registry is
    in-memory and bounded, and an id that is not in it is refused.

    That is a narrower gate than the bank allowlist rather than a wider one: the bank has
    14 permanent entries, this has at most `runs.MAX_RUNS` and only ones this process
    minted. The shape check runs first so a malformed string is refused at the door instead
    of becoming a dictionary key, and so the 404 for "wrong shape" and the 404 for "no such
    run" are the same answer to a caller — which is deliberate, since distinguishing them
    would confirm which ids exist.
    """
    if not _RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(status_code=404, detail=_UNKNOWN_RUN)
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=_UNKNOWN_RUN)
    return run


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> Any:
    """A run's current state. The polling fallback for a client with no `EventSource`.

    **A `GET` here calls no model**, exactly like every other read on this service: it
    returns what the background task has recorded so far. C4.9's rule is about the read
    path as a whole, not about one route.
    """
    # Runs are in-memory (ADR-011) and bounded, so an id from before a restart is gone
    # rather than wrong. 404 with the reason beats 404 with nothing.
    return _checked_run_id(run_id).public()


@app.get("/api/runs/{run_id}/report")
def run_report(run_id: str) -> Any:
    """The report a live run produced. **Flagged `live: true` in the payload, not the UI.**

    Without this route E2's "end to end" stopped one step short: a run completed, the
    stream said `done`, and the object it had just built was unreachable in memory.

    **The flag is on the data for the same reason `/api/replay` puts `illustrative` there.**
    This report is a fourth provenance category. It is not a published measurement — it is
    not in `out/reports`, it carries no `measurement_context`, it was never stamped by
    `make stamp-reports`, and its numbers are from one unrepeated run on whatever the pin
    happened to be. It is also not an authored fixture, because a real model really produced
    it. Rendering it identically to a cached report would show a reader fresh numbers with a
    published report's authority, which is the single most damaging thing this surface could
    do — and it would travel, because the object goes to a download and possibly a
    screenshot.
    """
    run = _checked_run_id(run_id)
    if run.report is None:
        raise HTTPException(
            status_code=409,
            detail=f"run is {run.status}; no report to serve"
            + (f": {run.error}" if run.error else ""),
        )
    return {
        "live": True,
        "run_id": run.run_id,
        "note": (
            "A live re-run. NOT a published measurement: no measurement_context, not "
            "stamped, one unrepeated run. Compare with /api/report/{id} for the cached one."
        ),
        "est_cost_usd": None,
        "analysis_calls": run.calls,
        "report": run.report,
    }


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    """The progress stream — E2's SSE half.

    Replays the run from its first event and then streams live ones, always terminating
    with an `end` frame. See `runs.subscribe` for why replay is load-bearing rather than
    a convenience.
    """
    run = _checked_run_id(run_id)
    return StreamingResponse(
        runs.subscribe(run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            # Nothing in this demo sits behind nginx, but a buffering proxy is the classic
            # way an SSE stream turns into one big response at the end -- which looks
            # exactly like the progress UI being broken.
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------- the static mount (FE-9)
#
# **The README has claimed since it was written that "`frontend/` is a static export mounted
# by the backend", and until now it was not.** `FRONTEND_OUT` was defined and never read.
# That is the same defect class as `app.py` citing a `test_api.py` that did not exist: a
# claim a reader cannot check is worse than no claim, because it stops them checking.
#
# **Why same-origin matters here and is not deployment tidiness.** ADR-003 deleted the
# hosted service, so the demo is one laptop serving one origin. If the page were opened from
# `file://` while the API answered on `http://127.0.0.1:8000`, every fetch would be
# cross-origin and the honest fix would be CORS — widening the surface of a backend whose
# entire security posture is "the only visitor-controlled input is an item id validated
# against a static allowlist". Serving both from one origin means that surface stays shut.
#
# **Registered last, deliberately.** Starlette matches routes in registration order, so a
# mount at "/" declared here cannot shadow `/api/*`, `/healthz` or `/readyz` above it. That
# ordering is asserted in `test_api.py` rather than left to a reader to infer from position.
#
# **Mounted only if the export exists**, because `make backend-tests`, CI and a fresh
# checkout all run with no `frontend/out`, and a backend that refused to start without a
# frontend build would make the API's own tests depend on the toolchain the API does not
# need. The consequence is stated rather than hidden: the mount is resolved at import time,
# so building the frontend while the server is running requires a restart -- runbook P1.
if FRONTEND_OUT.is_dir():
    from fastapi.staticfiles import StaticFiles

    # `html=True` resolves `items/mb-01/` to `items/mb-01/index.html`, which is the layout
    # `trailingSlash: true` produces, and serves `404.html` for an unknown path so a
    # mistyped URL gets the site's own page rather than a bare JSON error.
    app.mount("/", StaticFiles(directory=FRONTEND_OUT, html=True), name="frontend")
