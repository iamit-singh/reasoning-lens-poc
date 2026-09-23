"""Acceptance against a running server — C7.3, B7.3 Step 7. Owner: M3-4, used by M3-1a.

There is no manual gate and no staging tier (B0 Condition #2), so **this script is the
whole of deploy acceptance.** It runs against a URL over HTTP rather than in-process,
because the failures it exists to catch — a route that 500s on startup, a cache the server
cannot see from its own working directory, a breaker file it cannot write — are all
failures that an in-process test client papers over by sharing the caller's process.

The provider key is the point
-----------------------------
M3-1a's DoD is *"smoke subset green with the provider key removed"*, and `--no-key` asserts
exactly that: with `OPENAI_API_KEY` unset in the server's environment, every read path must
still be green. That is the **G3 fallback product** — the thing that ships if the live
re-run path is not ready, if the key expires the morning of the demo, or if the network in
the room is hostile. It is not a degraded mode to apologise for; C10.4 names it as a
launch branch.

A check that cannot fail is not a check, so each one names what it would catch.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        self.rows.append((ok, name, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
        return ok

    @property
    def failed(self) -> list[tuple[bool, str, str]]:
        return [r for r in self.rows if not r[0]]


def get(base: str, path: str, timeout: float = 10.0) -> tuple[int, object]:
    req = urllib.request.Request(base.rstrip("/") + path)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except Exception:
            return exc.code, None
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def post(base: str, path: str, payload: dict) -> tuple[int, object]:
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except Exception:
            return exc.code, None
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=os.environ.get("SMOKE_URL", "http://localhost:8000"))
    ap.add_argument(
        "--no-key",
        action="store_true",
        help="assert the read paths are green with no provider key (M3-1a's DoD)",
    )
    ap.add_argument("--wait", type=float, default=20.0, help="seconds to wait for /healthz")
    args = ap.parse_args(argv)
    base = args.base_url
    r = Result()

    print(f"smoke: {base}")

    # ---------------------------------------------------------------- liveness
    deadline = time.time() + args.wait
    alive = False
    while time.time() < deadline:
        status, _ = get(base, "/healthz", timeout=2)
        if status == 200:
            alive = True
            break
        time.sleep(0.5)
    if not r.check(alive, "healthz", f"no 200 within {args.wait:.0f}s" if not alive else ""):
        print("\nsmoke: the server is not up. Nothing below can be trusted.", file=sys.stderr)
        return 1

    # ---------------------------------------------------------------- readiness
    status, ready = get(base, "/readyz")
    ready = ready if isinstance(ready, dict) else {}
    r.check(status == 200, "readyz responds", f"status {status}")
    # Catches: a demo starting with an empty cache and nothing to show.
    r.check(
        bool(ready.get("cached_reports")),
        "cache is populated",
        f"{ready.get('cached_reports', 0)} reports — run `make report`",
    )
    # Catches: reports built by a pipeline that is not the one running (M3-2b, ADR-011).
    stale = ready.get("stale_reports") or []
    r.check(not stale, "no stale reports", f"{len(stale)} stale: {stale[:2]}")

    # ---------------------------------------------------------------- three items, one per tag
    status, bank = get(base, "/api/bank")
    bank = bank if isinstance(bank, dict) else {}
    by_tag = bank.get("by_tag") or {}
    r.check(status == 200 and bool(by_tag), "bank serves", f"{len(by_tag)} tags")

    cached_ids = {i["id"] for i in bank.get("items", []) if i.get("cached")}
    picked: list[str] = []
    for _tag, ids in sorted(by_tag.items()):
        hit = next((i for i in ids if i in cached_ids), None)
        if hit and hit not in picked:
            picked.append(hit)
        if len(picked) == 3:
            break
    r.check(len(picked) == 3, "three cached items across tags", f"picked {picked}")

    for item_id in picked:
        started = time.time()
        status, report = get(base, f"/api/report/{item_id}")
        elapsed = time.time() - started
        ok = status == 200 and isinstance(report, dict) and report.get("arms")
        # Catches: a read that silently became a generation. B4 #8 prices the cached path
        # at p90 under 5s, and this is the crude floor under that promise.
        r.check(bool(ok), f"report {item_id}", f"{elapsed:.2f}s, status {status}")
        r.check(elapsed < 5.0, f"report {item_id} under 5s", f"{elapsed:.2f}s")

    # ---------------------------------------------------------------- download
    if picked:
        status, _blob = get(base, f"/api/report/{picked[0]}/download")
        r.check(status == 200, "report download", f"status {status}")

    # ---------------------------------------------------------------- the published pages
    status, _calib = get(base, "/api/calibration")
    # **503 is this surface's convention for "not produced yet"**, and it is consistent
    # across both measurement artifacts: the capability exists and the measurement has not
    # been made. Before M2-17 and M2-9 that is the correct answer, and the pages render
    # "not yet measured" from it. What these catch is a 500 — a route that throws rather
    # than one that has nothing to say.
    r.check(status in (200, 503), "calibration endpoint", f"status {status}")
    status, _ = get(base, "/api/faithfulness")
    r.check(status in (200, 503), "faithfulness endpoint", f"status {status}")

    # ---------------------------------------------------------------- the guards
    status, body = post(base, "/api/runs", {"item_id": "mb-01"})
    body = body if isinstance(body, dict) else {}
    detail = str(body.get("detail", ""))
    # Either the kill switch is on (cached) or the breaker answered. Both are green; a 200
    # or a 500 is not. Catches a live path that is open when it should not be.
    # **Under --no-key a 202 is a FAIL, not a pass.** Generation is local and needs no key,
    # so a server without one will happily start a run and fail at classification — after
    # spending the compute. "Guarded" has to mean refused up front.
    allowed = (503, 429) if args.no_key else (503, 202, 429)
    r.check(
        status in allowed,
        "live-run path is guarded" + (" (refused without a key)" if args.no_key else ""),
        f"status {status}: {detail[:70]}",
    )

    status, body = post(base, "/api/runs", {"item_id": "../../etc/passwd"})
    r.check(status != 202, "run route rejects a traversal id", f"status {status}")

    # ---------------------------------------------------------------- E2's stream (M3-1b)
    # The progress routes are READS and must behave like every other read here: no model
    # call, and an id that is not a live run gets the same 404 whatever shape it had.
    # Checked against a real server because the shape guard and the registry lookup are
    # two different refusals that have to be indistinguishable from outside.
    status, _ = get(base, "/api/runs/run-deadbeef")
    r.check(status == 404, "an unknown run id is 404", f"status {status}")

    status, _ = get(base, "/api/runs/..%2f..%2fetc%2fpasswd")
    r.check(status in (404, 405), "a malformed run id is refused", f"status {status}")

    status, _ = get(base, "/api/runs/run-deadbeef/events")
    r.check(status == 404, "the event stream refuses an unknown run", f"status {status}")

    # `live_run_budget` is the guard standing in for a dollar breaker the price table
    # cannot feed. An operator reading `spent_usd: 0.0` needs to see why it is zero.
    status, body = get(base, "/readyz")
    budget = (body or {}).get("live_run_budget") if isinstance(body, dict) else None
    r.check(
        isinstance(budget, dict) and budget.get("analysis_calls_limit", 0) > 0,
        "readiness reports the live-run CALL budget, not just dollars",
        f"{budget}",
    )

    # ---------------------------------------------------------------- the static mount (FE-9)
    # The whole demo is "one laptop, one origin". These run against a REAL server rather
    # than a TestClient because the failure they catch -- a mount resolved at import time
    # against a directory that was not built yet -- cannot happen in-process, where the
    # fixture always imports after the build.
    status, body = get(base, "/")
    served = status == 200 and isinstance(body, bytes) and b"Reasoning Lens" in body
    _, ready = get(base, "/readyz")
    mounted = isinstance(ready, dict) and ready.get("frontend_mounted") is True
    if not mounted:
        # Not a failure: `make smoke` is the API's acceptance test and must pass on a
        # checkout that has never run the frontend toolchain. Saying so beats a green tick
        # over a page nobody served.
        r.check(True, "frontend mount SKIPPED (no frontend/out)", "run `make fe-build-measured`")
    else:
        r.check(served, "the built site is served from the API's own origin", f"status {status}")
        status, _ = get(base, "/items/mb-01/")
        r.check(status == 200, "an item page resolves through the mount", f"status {status}")
        # The mount is the first route on this service that takes a path from a visitor.
        status, body = get(base, "/../.env")
        leaked = isinstance(body, bytes) and b"OPENAI_API_KEY" in body
        r.check(
            status != 200 and not leaked,
            "traversal out of the export is refused",
            f"status {status}",
        )
        # Registration order, from the outside: if the mount had shadowed the API this
        # would come back as the site's 404 page instead of JSON.
        status, body = get(base, "/api/bank")
        r.check(
            status == 200 and isinstance(body, dict),
            "the mount does not shadow /api",
            f"status {status}, {type(body).__name__}",
        )

    # ---------------------------------------------------------------- the no-key claim
    if args.no_key:
        # Every check above is a read path. If they are green and the server has no key,
        # the G3 fallback product is proven rather than asserted.
        reads_green = all(ok for ok, name, _ in r.rows if "live-run" not in name)
        r.check(
            reads_green,
            "READ PATHS GREEN WITH NO PROVIDER KEY",
            "M3-1a's DoD — this is the G3-cached product",
        )

    print()
    if r.failed:
        print(f"smoke: {len(r.failed)} of {len(r.rows)} checks FAILED", file=sys.stderr)
        return 1
    print(f"smoke: {len(r.rows)}/{len(r.rows)} checks passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
