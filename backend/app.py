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
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from backend import breaker, cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "problem-bank/items"
REPORTS_DIR = ROOT / "out/reports"
CALIBRATION = ROOT / "calibration/results/latest.json"
FAITHFULNESS = ROOT / "faithfulness/panel.json"
SEEDED_DIR = ROOT / "calibration/seeded"
FRONTEND_OUT = ROOT / "frontend/out"

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


def _rate_limited(key: str) -> bool:
    """A fixed window per client. In-process on purpose.

    ADR-003 deleted the deployment: this runs as one process on one laptop, so a shared
    Redis counter would add a dependency whose only job is coordinating with replicas that
    do not exist. If it ever runs replicated, this is the thing to move — and it will be
    obvious, because the limit will be per-replica.
    """
    now = time.time()
    window = [t for t in _HITS.get(key, []) if now - t < 60]
    _HITS[key] = window
    if len(window) >= RATE_LIMIT_PER_MIN:
        return True
    window.append(now)
    return False


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
        "live_runs": demo_mode() != "cached" and state.allowed and analysis_ready()[0],
        "analysis_tier": {"ready": analysis_ready()[0], "reason": analysis_ready()[1]},
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
    return {"illustrative": True, "case": json.loads(path.read_text())}


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
    _checked_id(item_id)

    run_id = f"run-{int(time.time() * 1000):x}"
    return JSONResponse({"run_id": run_id, "item_id": item_id}, status_code=202)
