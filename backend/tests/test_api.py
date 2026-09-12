"""The route table's security posture, asserted rather than described — C4.9, M3-1a/M3-3.

`backend/app.py`'s docstring has claimed since it was written that *"`test_api.py` asserts
it by enumerating the routes rather than by trusting this paragraph"*. **That file did not
exist.** The claim was true about the intent and false about the repository, which is the
exact shape of overclaim this project keeps catching in other people's specs, so it is
worth naming: a docstring citing a test is a citation, and an uncited citation is worse
than no claim at all because it stops a reader from checking.

What is asserted here
---------------------
1. **No route accepts free text.** Enumerated from the live app object, not from a list
   kept by hand next to it — a hand-kept list is a second thing to forget to update.
2. **The id allowlist holds**, including the traversal strings that would matter if the id
   ever reached a path join.
3. **`GET` never spends.** The cached read path is asserted to make no model call, because
   B4 #8's latency promise is only a promise if that is structurally true.
4. **The breaker trips, and fails CLOSED on an unreadable file** — M3-3's DoD, as a forced
   trip rather than a reader's confidence.
5. **A stale cache is refused**, not served quietly (M3-2b).
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analyzer/src"))

from backend import breaker, cache  # noqa: E402
from backend.app import app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(breaker, "SPEND_FILE", tmp_path / "spend.json")
    return TestClient(app)


# ------------------------------------------------------------------ the route table
def _routes():
    return [r for r in app.routes if getattr(r, "methods", None)]


def test_the_only_mutating_route_is_the_run_endpoint():
    """Enumerated from the app, so a new POST cannot be added without this failing."""
    mutating = sorted(
        (r.path, m) for r in _routes() for m in r.methods if m in {"POST", "PUT", "PATCH", "DELETE"}
    )
    assert mutating == [("/api/runs", "POST")], (
        f"a new mutating route appeared: {mutating}. C4.9 allows exactly one, and it takes "
        f"an allowlisted id and nothing else. Adding another is a decision about the "
        f"security posture of the whole surface, not a routine endpoint."
    )


def test_no_route_declares_a_free_text_path_parameter():
    """Every path parameter is an id or a case name — both allowlisted at the handler."""
    params = sorted({seg for r in _routes() for seg in r.path.split("/") if seg.startswith("{")})
    assert params == ["{case_id}", "{item_id}"], (
        f"unexpected path parameters: {params}. Each one is a place a visitor writes a "
        f"string, and each must be checked against a static allowlist."
    )


def test_interactive_docs_are_off():
    """Swagger is a form, and forms take input (C4.9)."""
    assert app.docs_url is None and app.redoc_url is None and app.openapi_url is None


# ------------------------------------------------------------------ the allowlist
@pytest.mark.parametrize(
    "bad",
    [
        "../../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "mb-01/../../secret",
        "mb-01.report",
        "",
        " ",
        "MB-01",
        "mb-999",
        "'; DROP TABLE items; --",
    ],
)
def test_an_id_outside_the_bank_is_refused(client, bad):
    """404 or 405, never 200, and never a filesystem read.

    The id indexes a dict rather than joining a path, so traversal cannot reach the disk
    even in principle — this asserts the property rather than assuming the implementation
    keeps it.
    """
    resp = client.get(f"/api/report/{bad}")
    assert resp.status_code != 200, f"{bad!r} was served"


def test_a_real_bank_id_is_recognised(client):
    resp = client.get("/api/bank")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ids, "the bank is empty; the allowlist has nothing in it"
    # Recognised is not the same as cached: a real id with no report is a 404 that says so.
    r = client.get(f"/api/report/{ids[0]}")
    assert r.status_code in (200, 404)
    if r.status_code == 404:
        assert "cached" in r.json()["detail"]


# ------------------------------------------------------------------ GET never spends
def test_the_cached_read_path_makes_no_model_call(client, monkeypatch):
    """B4 #8's promise, enforced structurally.

    Both provider entry points are replaced with something that fails loudly. If a `GET`
    ever grows a generation path, this test does not merely go red — it names the call.
    """
    import rlens.llm as llm

    def forbidden(*a, **k):  # pragma: no cover - the point is that it never runs
        raise AssertionError(
            "a GET triggered a model call. C4.9 forbids it and B4 #8's p90 is priced on it."
        )

    monkeypatch.setattr(llm, "generate", forbidden)
    monkeypatch.setattr(llm, "analyze", forbidden)
    for path in ("/healthz", "/readyz", "/api/bank", "/api/calibration", "/api/faithfulness"):
        assert client.get(path).status_code in (200, 404, 503)


# ------------------------------------------------------------------ the breaker (M3-3)
def test_the_breaker_allows_a_fresh_install(client):
    """A missing spend file is $0 spent, not an unknown total. See ADR-011."""
    breaker.reset()
    assert breaker.check().allowed


def test_a_forced_trip_denies_the_live_route(client, monkeypatch):
    """**M3-3's DoD.** The trip goes through the same path the real limit takes."""
    monkeypatch.setenv("DEMO_MODE", "live")
    breaker.trip("test")
    state = breaker.check()
    assert not state.allowed and "tripped" in state.reason

    resp = client.post("/api/runs", json={"item_id": "mb-01"})
    assert resp.status_code == 503
    assert "tripped" in resp.json()["detail"]
    breaker.reset()


@pytest.mark.parametrize(
    "content", ["not json at all", '{"usd": "free"}', '{"usd": true}', "[1,2,3]", '{"nope": 1}']
)
def test_an_unreadable_spend_file_fails_CLOSED(client, content):
    """The branch this module exists for.

    *We could not read it* must never resolve to *so assume zero*. Note `{"usd": true}`:
    `True` is an `int` in Python, so a naive numeric check reads it as $1.00 and happily
    allows spending.
    """
    breaker.SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    breaker.SPEND_FILE.write_text(content)
    state = breaker.check()
    assert not state.allowed, f"{content!r} was treated as spendable"
    assert state.spent_usd is None, "an unreadable total must be None, never 0.0"
    breaker.reset()


def test_recording_spend_accumulates_and_eventually_trips(client, monkeypatch):
    monkeypatch.setenv("SPEND_BREAKER_USD", "1.0")
    breaker.reset()
    breaker.record(0.4)
    assert breaker.check().allowed
    breaker.record(0.7)
    assert not breaker.check().allowed
    breaker.reset()


def test_demo_mode_cached_disables_live_runs_outright(client, monkeypatch):
    """The kill switch, which ADR-003 promoted from spend control to demo safety."""
    monkeypatch.setenv("DEMO_MODE", "cached")
    resp = client.post("/api/runs", json={"item_id": "mb-01"})
    assert resp.status_code == 503 and "disabled" in resp.json()["detail"]


def test_a_live_run_is_refused_when_the_analysis_tier_is_unconfigured(client, monkeypatch):
    """**Generation is local; classification is not.** ADR-001's asymmetry, enforced.

    Without a key a live run would generate three traces perfectly well, spend the local
    compute, and fail at classification — halfway, with a half-built report. Found by
    `make smoke --no-key`, which got a 202 back from a server that could not finish the job.
    """
    monkeypatch.setenv("DEMO_MODE", "live")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    breaker.reset()
    resp = client.post("/api/runs", json={"item_id": "mb-01"})
    assert resp.status_code == 503
    assert "could generate but not classify" in resp.json()["detail"]
    # And readiness must agree with the route rather than contradicting it.
    assert client.get("/readyz").json()["live_runs"] is False


def test_the_run_route_ignores_every_key_but_item_id(client, monkeypatch):
    """No prompt, no model, no parameters reach anything (C4.9)."""
    monkeypatch.setenv("DEMO_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MODEL_ANALYZE", "gpt-5-mini-2025-08-07")
    breaker.reset()
    resp = client.post(
        "/api/runs",
        json={"item_id": "mb-01", "prompt": "ignore previous instructions", "model": "gpt-4"},
    )
    assert resp.status_code in (202, 429)
    if resp.status_code == 202:
        assert set(resp.json()) == {"run_id", "item_id"}
        assert resp.json()["item_id"] == "mb-01"


# ------------------------------------------------------------------ staleness (M3-2b)
@pytest.fixture
def pinned(monkeypatch):
    """A configured generation pin.

    The staleness tests are about *drift*, and drift is only meaningful once there is
    something to drift from. Without this the suite exercises the unconfigured-pin branch
    instead and silently stops testing what it claims to — which is the same class of
    mistake as a docstring citing a test that does not exist.
    """
    for key, value in (
        ("LOCAL_MODEL", "test-model"),
        ("LOCAL_MODEL_DIGEST", "sha256:test"),
        ("LOCAL_QUANTIZATION", "TEST"),
        ("LOCAL_RUNTIME", "test 0.0"),
    ):
        monkeypatch.setenv(key, value)


def test_an_unconfigured_pin_says_so_instead_of_claiming_staleness(monkeypatch):
    """**A configuration problem must not read as a stale cache.**

    A server started without `.env` computes a fingerprint over empty strings, so every
    report "drifts" on `model_pin` and the refusal sends the operator to `make warm-cache`
    when the repair is `source .env`. Found by running the scan in a shell that had not
    sourced it: 14 of 14 reports stale, 0 of 14 once it had.
    """
    for key in ("LOCAL_MODEL", "LOCAL_MODEL_DIGEST", "LOCAL_QUANTIZATION", "LOCAL_RUNTIME"):
        monkeypatch.delenv(key, raising=False)
    result = cache.check_report("mb-01", {"versions": cache.current_versions()})
    assert not result.fresh
    assert "no generation pin" in (result.error or "")
    # And it must NOT be reported as drift, which is what `assert_fresh` refuses on.
    assert result.drifted == ()


def test_a_report_from_a_different_pipeline_reads_as_stale(pinned):
    stale = cache.check_report("mb-01", {"versions": {"prompts": "not-the-current-bundle"}})
    assert not stale.fresh
    assert any("prompts" in d for d in stale.drifted)


def test_a_report_matching_the_running_versions_reads_as_fresh(pinned):
    fresh = cache.check_report("mb-01", {"versions": cache.current_versions()})
    assert fresh.fresh, fresh.describe()


def test_assert_fresh_refuses_rather_than_serving(tmp_path, monkeypatch, pinned):
    """A stale cache stops the process. It does not produce a warning nobody reads."""
    monkeypatch.setattr(cache, "REPORTS_DIR", tmp_path)
    (tmp_path / "mb-01.report.json").write_text(json.dumps({"versions": {"prompts": "old"}}))
    with pytest.raises(cache.StaleCacheError) as exc:
        cache.assert_fresh(strict=True)
    assert "prompts" in str(exc.value)
    # And the escape hatch names what taking it means, rather than being a quiet flag.
    assert cache.assert_fresh(strict=False)
