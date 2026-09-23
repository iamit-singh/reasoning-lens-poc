#!/usr/bin/env python3
"""E15 / M3-6 — record the fallback demo video. Run: `make demo-video`.

C10.4 books a fallback video because **a local demo has more single points of failure than
a hosted one, not fewer**. [Amendment 002 §4](../../plan-amendment-002-no-human-capacity.md)
cut it to *an unedited screen capture*, on one condition: **"if the demo runs headless;
otherwise unmade."** On 18 Sep it did not — no driver on the machine — and installing one
for a non-gating artifact was not a call to take unilaterally, so M3-6 recorded it as unmade
with its reason. The condition is met now, so it is made.

**Unedited is a property of this script, not a promise.** One browser context, one
continuous recording, no cuts and no post-processing: the file is whatever the pages did.
The tour below scrolls and waits; it never types a number, never opens a devtools overlay,
and never touches a surface the demo would not show.

What this insures against, stated precisely, because the gap is the interesting part
--------------------------------------------------------------------------------------
`make fe-export-check` already proves the demo survives a **dead backend** by construction —
it reads the built artifact with every `<script>` stripped and asserts the words are still
there. That is stronger than a recording.

A recording additionally survives a **dead laptop**, and that is the whole of what it adds.
Whoever demos this should know which half is covered by which artifact.

**This is the cached read path and nothing else.** No model is called, and the provider key
is stripped from the server this drives, for the same reason `make smoke` strips it: *we did
not call it* and *we could not call it* are different claims. A viewer watching this is
watching the fallback product, which is what ADR-003 made the shipping product.

On the browser
--------------
Playwright pins a Chromium revision per release and this machine's cache holds newer builds
than the installed client asks for. Downloading a fifth copy to satisfy an exact-match rule
would be ~150 MB for a non-gating artifact, so the newest cached build is used instead —
and **which build it was is printed and written into the sidecar**, never silently
substituted. A recording is evidence, and evidence that cannot say what produced it is
decoration.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_VIDEO = ROOT / "docs/demo-fallback.webm"
OUT_SIDECAR = ROOT / "docs/demo-fallback.json"
SERVER_LOG = ROOT / "out/.video-server.log"
CACHE = pathlib.Path.home() / "Library/Caches/ms-playwright"

#: The tour, in the order the demo is given. Each entry is (path, dwell seconds, scroll?).
#:
#: It follows the arrival order a reader actually meets — the landing page first, because
#: that is the one screen everybody sees — and then the two surfaces the heuristic
#: walkthrough review singled out as the strongest things on the site: the calibration page
#: that leads with its own shortfall, and the faithfulness panel that publishes 0 of 48.
#: The item page in between is where a step is shown to be fluent and still not hold up.
TOUR = [
    ("/", 9.0, True),
    ("/items/mb-08/", 9.0, True),
    ("/items/mb-06/", 9.0, True),
    ("/calibration/", 10.0, True),
    ("/faithfulness/", 8.0, True),
]


def find_chromium() -> tuple[str | None, str]:
    """The browser to drive, and a human-readable note about where it came from."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            want = pathlib.Path(p.chromium.executable_path)
        if want.exists():
            return str(want), f"playwright's own pinned build ({want.parent.parent.name})"
    except Exception:  # probed, not required
        pass

    if not CACHE.is_dir():
        return None, "no ms-playwright cache on this machine"
    builds = sorted(
        (d for d in CACHE.glob("chromium-*") if d.is_dir()),
        key=lambda d: int(re.sub(r"\D", "", d.name) or 0),
        reverse=True,
    )
    for build in builds:
        for exe in build.rglob("*/Contents/MacOS/*"):
            if exe.is_file() and os.access(exe, os.X_OK):
                return str(exe), f"newest cached build {build.name} (client pins a different one)"
        for exe in build.rglob("chrome"):
            if exe.is_file() and os.access(exe, os.X_OK):
                return str(exe), f"newest cached build {build.name} (client pins a different one)"
    return None, "no usable chromium in the ms-playwright cache"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def start_server(port: int) -> subprocess.Popen:
    """The demo as P1 brings it up — one origin serving the page and the API (FE-9).

    **`.env` is loaded by the shell, not parsed here**, and the line below is deliberately
    the same `set -a; . ./.env; set +a` that `make serve-api` and `make smoke` use.

    The first version of this function re-implemented the parse in Python and got it wrong
    within one run: `.env` carries trailing inline comments, so `SPEND_BREAKER_USD=10  #
    was 150...` arrived at the breaker as the whole string and `/readyz` died on
    `float()`. The shell strips that comment; a hand-rolled parser has to be told to, and
    every other quoting rule besides. A second interpreter of the same file is a second
    thing that can disagree with it, which is how the repo ends up with an environment that
    works under `make` and nowhere else — M3-5c found that exact shape twice.

    `OPENAI_API_KEY` is unset AFTER sourcing, so it is stripped rather than merely unused:
    *we did not call the provider* and *we could not call the provider* are different
    claims, and only the second is the one this recording makes.
    """
    cmd = (
        "set -a; [ -f .env ] && . ./.env; set +a; "
        "unset OPENAI_API_KEY; "
        f'exec "{ROOT}/.venv/bin/python" -m uvicorn backend.app:app '
        f"--host 127.0.0.1 --port {port}"
    )
    # The server's output is KEPT, not discarded. M3-2b's trap is that a process which has
    # not loaded `.env` computes its freshness fingerprint over empty strings, reads every
    # report as stale and refuses to start -- and the refusal names the wrong repair. A
    # recorder that swallowed that would report "never became ready" and send the operator
    # looking in the wrong place, which is the same defect one level up.
    return subprocess.Popen(
        ["bash", "-c", cmd],
        cwd=ROOT,
        stdout=SERVER_LOG.open("w"),
        stderr=subprocess.STDOUT,
    )


def readyz(base: str, tries: int = 60) -> dict | None:
    for _ in range(tries):
        try:
            with urllib.request.urlopen(f"{base}/readyz", timeout=2) as r:
                return json.loads(r.read())
        except Exception:  # still starting
            time.sleep(0.25)
    return None


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", help="drive an already-running demo instead of starting one")
    ap.add_argument("--out", default=str(OUT_VIDEO))
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "record-demo-video: playwright is not installed for this interpreter.\n"
            "\n"
            "  It is a DEMO-ONLY dependency and deliberately not in the analyzer's\n"
            "  requirements: M3-5c's cold run found undeclared deps are how this repo\n"
            "  breaks for everyone but its author, and the repair is to declare them in\n"
            "  their own file rather than to widen the package's.\n"
            "\n"
            "    pip install -r scripts/requirements-video.txt\n"
            "    playwright install chromium     # only if no build is cached already\n",
            file=sys.stderr,
        )
        return 2

    exe, provenance = find_chromium()
    if not exe:
        print(
            f"record-demo-video: {provenance}.\n  Run: playwright install chromium", file=sys.stderr
        )
        return 2
    print(f"record-demo-video: browser — {provenance}")

    out = pathlib.Path(args.out)
    tmp = ROOT / "out/.video"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    proc = None
    base = args.base_url
    if not base:
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        proc = start_server(port)

    try:
        health = readyz(base)
        if not health:
            print(f"record-demo-video: {base} never became ready", file=sys.stderr)
            if proc and SERVER_LOG.exists():
                print("--- server output ---", file=sys.stderr)
                print("\n".join(SERVER_LOG.read_text().splitlines()[-25:]), file=sys.stderr)
            return 1
        if not health.get("frontend_mounted"):
            print(
                "record-demo-video: the server is up but no static export is mounted.\n"
                "  Run `make fe-build-measured` first — a recording of a 404 is worse\n"
                "  than no recording.",
                file=sys.stderr,
            )
            return 1
        if health.get("stale_reports"):
            print(
                f"record-demo-video: REFUSING — {len(health['stale_reports'])} stale "
                "report(s). A recording of numbers attributed to a system that is no "
                "longer running is the most misleading artifact this repo could ship.",
                file=sys.stderr,
            )
            return 1
        print(
            f"record-demo-video: {health['cached_reports']} cached reports, 0 stale, "
            f"analysis tier ready={health['analysis_tier']['ready']} "
            f"({health['analysis_tier'].get('reason', 'n/a')})"
        )

        visited = []
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=exe)
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(tmp),
                record_video_size={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            for path, dwell, scroll in TOUR:
                resp = page.goto(f"{base}{path}", wait_until="load")
                status = resp.status if resp else 0
                visited.append({"path": path, "status": status})
                if status != 200:
                    print(f"record-demo-video: {path} returned {status}", file=sys.stderr)
                page.wait_for_timeout(int(dwell * 400))
                if scroll:
                    # A slow scroll rather than a jump: the recording is for someone
                    # reading it, and an instant page-end is unreadable at 25fps.
                    height = page.evaluate("document.body.scrollHeight")
                    for y in range(0, int(height), 110):
                        page.evaluate(f"window.scrollTo(0,{y})")
                        page.wait_for_timeout(45)
                    page.wait_for_timeout(int(dwell * 300))
                    page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(500)
            ctx.close()
            browser.close()

        webm = sorted(tmp.glob("*.webm"))
        if not webm:
            print("record-demo-video: no video was produced", file=sys.stderr)
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(webm[0]), out)
        size = out.stat().st_size

        bad = [v for v in visited if v["status"] != 200]
        sidecar = {
            "_README": (
                "Provenance for docs/demo-fallback.webm (E15). An unedited single-pass "
                "screen capture of the CACHED read path with the provider key stripped — "
                "no model was called and none could be. Regenerate with `make demo-video`."
            ),
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "commit": git("rev-parse", "HEAD"),
            # **The recorder's own two outputs are excluded from this.** Counting them
            # would make the field false on every run by construction, and a field that is
            # always false says nothing -- the reader needs to know whether the SOURCE that
            # produced these frames was committed, which is the question "does this
            # recording correspond to `commit`" actually turns on.
            "tree_clean": not [
                ln
                for ln in git("status", "--porcelain").splitlines()
                if ln.strip() and not ln.split()[-1].startswith("docs/demo-fallback.")
            ],
            "browser": provenance,
            "viewport": "1280x800",
            "bytes": size,
            "pages": visited,
            "readyz": health,
            "edited": False,
        }
        OUT_SIDECAR.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n")

        print(
            f"record-demo-video: wrote {out.relative_to(ROOT)} ({size / 1024:.0f} KB) "
            f"+ {OUT_SIDECAR.name}"
        )
        if bad:
            print(
                f"record-demo-video: FAIL — {len(bad)} page(s) did not return 200: {bad}",
                file=sys.stderr,
            )
            return 1
        print("record-demo-video: PASS — 5 surfaces, one continuous pass, nothing edited.")
        return 0
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
