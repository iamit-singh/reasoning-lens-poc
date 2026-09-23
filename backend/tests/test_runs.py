"""E2's progress stream — the SSE sequence test C10.4 budgeted and M3-1b never wrote.

Owner: M3-1b.

**Nothing here calls a model.** Every test stubs `runs._execute`, because the thing under
test is the *stream and its guarantees*, not the pipeline — and a test that drove the real
executor would run the local model and then a paid classification call on every CI run.
That is the same reason `test_api.py` stubs it.

The two properties worth testing are the ones a reader cannot see by looking at the route:

1. **A late subscriber gets the whole sequence.** The early stages are the fast ones, so
   the common case is a viewer who connects during `classifying` — and a stream that only
   carried live events would show them a run that appears to begin in the middle.
2. **The stream always terminates.** A progress UI that never receives an end frame is
   indistinguishable from one that is still working.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from backend import app as app_mod
from backend import breaker, runs
from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    runs.reset_for_tests()
    breaker.reset()
    app_mod._HITS.clear()
    monkeypatch.setenv("DEMO_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MODEL_ANALYZE", "gpt-5-mini-2025-08-07")
    yield
    runs.reset_for_tests()


def _frames(text: str) -> list[dict]:
    """Parse an SSE body into (event, data) pairs, ignoring comments/heartbeats."""
    out = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(":"):
            continue
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if name and data:
            out.append({"event": name, **json.loads(data)})
    return out


def _stub(monkeypatch, sequence, *, status="done"):
    """Replace the executor with one that emits `sequence` and finishes."""

    async def _fake(run, item):
        for stage, st, detail in sequence:
            runs._emit(run, stage, st, detail)
        run.status = status
        if status == "failed":
            run.error = "stubbed failure"

    monkeypatch.setattr(runs, "_execute", _fake)


def test_the_stream_replays_the_whole_run_to_a_late_subscriber(client, monkeypatch):
    """**The property the UI depends on and the route cannot show.**

    The run is already finished before anything subscribes. A stream carrying only live
    events would hand this subscriber nothing at all.
    """
    _stub(
        monkeypatch,
        [
            ("generating", "started", "3 arms"),
            ("generating", "ok", "direct"),
            ("classifying", "ok", "direct"),
            ("assembling", "ok", "3 arms"),
        ],
    )
    run_id = client.post("/api/runs", json={"item_id": "mb-01"}).json()["run_id"]

    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = "".join(resp.iter_text())

    frames = _frames(body)
    progress = [f for f in frames if f["event"] == "progress"]
    assert [f["stage"] for f in progress] == [
        "accepted",
        "generating",
        "generating",
        "classifying",
        "assembling",
    ]
    # Monotonic and gapless, because a client orders on it.
    assert [f["seq"] for f in progress] == list(range(len(progress)))


def test_the_stream_always_ends(client, monkeypatch):
    """A progress UI that never gets an end frame looks exactly like one still working."""
    _stub(monkeypatch, [("generating", "ok", "direct")])
    run_id = client.post("/api/runs", json={"item_id": "mb-01"}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        frames = _frames("".join(resp.iter_text()))
    assert frames[-1]["event"] == "end"
    assert frames[-1]["status"] == "done"


def test_a_failed_run_ends_with_its_reason_rather_than_silence(client, monkeypatch):
    _stub(monkeypatch, [("generating", "failed", "the model did not answer")], status="failed")
    run_id = client.post("/api/runs", json={"item_id": "mb-01"}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        frames = _frames("".join(resp.iter_text()))
    end = frames[-1]
    assert end["event"] == "end" and end["status"] == "failed"
    assert end["error"] == "stubbed failure"
    assert any(f.get("status") == "failed" for f in frames if f["event"] == "progress")


def test_degraded_arms_are_reachable_on_the_stream(client, monkeypatch):
    """E2's *every degraded branch reachable*, at the transport rather than in a fixture.

    FE-8 already proves the degraded **states render**; this proves a live run can actually
    deliver one, which is the half that had no process to come from.
    """
    _stub(
        monkeypatch,
        [
            ("generating", "degraded", "react: no spans (timeout)"),
            ("classifying", "degraded", "thinking: analysis_unavailable"),
            ("assembling", "ok", "2 arms"),
        ],
    )
    run_id = client.post("/api/runs", json={"item_id": "mb-01"}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        frames = _frames("".join(resp.iter_text()))
    degraded = [f for f in frames if f.get("status") == "degraded"]
    assert len(degraded) == 2
    assert "analysis_unavailable" in " ".join(f["detail"] for f in degraded)


def test_the_status_route_calls_no_model_and_mirrors_the_stream(client, monkeypatch):
    """The polling fallback has to agree with the stream, or one of them is lying."""
    _stub(monkeypatch, [("generating", "ok", "direct"), ("assembling", "ok", "1 arm")])
    posted = client.post("/api/runs", json={"item_id": "mb-01"}).json()
    with client.stream("GET", posted["events_url"]) as resp:
        stream = [f for f in _frames("".join(resp.iter_text())) if f["event"] == "progress"]

    state = client.get(posted["status_url"]).json()
    assert state["status"] == "done"
    assert [e["seq"] for e in state["events"]] == [f["seq"] for f in stream]
    assert state["stages"] == list(runs.STAGES)


def test_the_cost_field_is_absent_rather_than_zero(client, monkeypatch):
    """**`0.0` would be a claim that the run was free.**

    `analyzer/prices.json` carries null rates deliberately, so no live run can report an
    honest dollar figure. The same argument `_cost()` makes for `est_cost_usd` in a report
    applies here, and it is the reason the call budget exists at all.
    """
    _stub(monkeypatch, [("assembling", "ok", "done")])
    posted = client.post("/api/runs", json={"item_id": "mb-01"}).json()
    state = client.get(posted["status_url"]).json()
    assert state["est_cost_usd"] is None
    assert "not priced" in state["cost_note"]
    assert client.get("/readyz").json()["live_run_budget"]["analysis_calls_limit"] > 0


def test_an_unknown_run_id_says_why_it_is_unknown(client):
    resp = client.get("/api/runs/run-deadbeef")
    assert resp.status_code == 404
    assert "restart" in resp.json()["detail"]
    assert client.get("/api/runs/run-deadbeef/events").status_code == 404


def test_the_process_call_budget_refuses_rather_than_spending(client, monkeypatch):
    """The guard standing in for a dollar breaker the price table cannot feed.

    Not a cosmetic limit: every admitted run is a paid classification call, and the
    breaker's own `spent_usd` cannot move because nothing can price it.
    """
    # Note this test does NOT stub `_execute`: it exercises the real budget branch, which
    # refuses before any generation or analysis call is made.
    monkeypatch.setattr(runs, "_PROCESS_CALLS", runs.LIVE_PROCESS_CALL_BUDGET)
    posted = client.post("/api/runs", json={"item_id": "mb-01"}).json()
    state = client.get(posted["status_url"]).json()
    assert state["status"] == "failed"
    assert "budget" in (state["error"] or "")
    assert state["analysis_calls"] == 0


def test_runs_are_bounded_so_a_long_demo_cannot_grow_without_limit(client, monkeypatch):
    _stub(monkeypatch, [("assembling", "ok", "done")])
    for _ in range(runs.MAX_RUNS + 5):
        app_mod._HITS.clear()
        client.post("/api/runs", json={"item_id": "mb-01"})
    assert len(runs._RUNS) <= runs.MAX_RUNS


def test_a_live_report_is_flagged_live_in_the_payload(client, monkeypatch):
    """**A live report is a fourth provenance category and must say so on the data.**

    Not in `out/reports`, no `measurement_context`, never stamped, one unrepeated run — and
    a real model really produced it, so it is not an authored fixture either. Rendering it
    with a published report's authority is the one thing this surface must not do, and the
    flag rides on the object because the object travels to a download and a screenshot.
    Same argument `/api/replay` makes for `illustrative`.
    """

    async def _fake(run, item):
        run.report = {"item": {"id": "mb-01"}, "arms": []}
        run.calls = 3
        run.status = "done"

    monkeypatch.setattr(runs, "_execute", _fake)
    posted = client.post("/api/runs", json={"item_id": "mb-01"}).json()

    assert client.get(posted["status_url"]).json()["report_available"] is True
    body = client.get(f"{posted['status_url']}/report").json()
    assert body["live"] is True
    assert body["est_cost_usd"] is None
    assert "NOT a published measurement" in body["note"]
    assert body["report"]["item"]["id"] == "mb-01"


def test_asking_for_a_report_before_there_is_one_says_why(client, monkeypatch):
    """409, with the run's own error — not 404, which would mean the run does not exist."""
    _stub(monkeypatch, [("generating", "failed", "boom")], status="failed")
    posted = client.post("/api/runs", json={"item_id": "mb-01"}).json()
    resp = client.get(f"{posted['status_url']}/report")
    assert resp.status_code == 409
    assert "stubbed failure" in resp.json()["detail"]
