#!/usr/bin/env python3
"""FE-10 — assert the static export renders with nothing running. Run: `make fe-export-check`.

C11.3 asks for a *server-rendered featured comparison on arrival*, and B4 #8 prices the
cached path at p90 under 5 seconds. With `output: "export"` both become the same claim:
**the content is in the HTML before a browser is involved**, so there is nothing to wait
for and nothing to be unreachable.

That claim is easy to make and easy to break — one `useEffect` that fetches, one
`"use client"` on a data component, and the page still *looks* right in dev while shipping
an empty shell that needs a backend. Neither `next build` nor the eye catches it, because
in dev the backend is running.

So this checks the built artifact the way a reader with no network gets it: **every
`<script>` stripped, then look for the words.** If the text is only in the JS payload, the
page needs JavaScript *and* whatever that JavaScript calls, and this fails.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend/out"

#: Phrases that must survive script-stripping, and the surface each one proves.
REQUIRED = [
    ("index.html", "Reasoning Lens", "the shell"),
    ("index.html", "Featured", "C11.3's featured comparison, server-rendered"),
    ("calibration/index.html", "Calibration", "FE-6"),
    ("faithfulness/index.html", "trials", "FE-5's headline, with its denominator"),
]

#: Hosts a page must never reach for at load. The export is opened from `file://` in the
#: fallback path, where any of these is a blank section rather than a slow one.
FORBIDDEN_IN_MARKUP = ["localhost:8000", "127.0.0.1:8000", "http://localhost"]


def visible_text(path: pathlib.Path) -> str:
    raw = path.read_text()
    body = re.sub(r"<script.*?</script>", " ", raw, flags=re.DOTALL)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.DOTALL)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    if not OUT.is_dir():
        print(f"no static export at {OUT}. Run `make fe-build` first.", file=sys.stderr)
        return 2

    failures: list[str] = []
    pages = sorted(OUT.rglob("index.html"))
    print(f"FE-10: {len(pages)} exported pages under {OUT.relative_to(ROOT)}")

    for rel, phrase, what in REQUIRED:
        path = OUT / rel
        if not path.exists():
            failures.append(f"{rel}: not exported at all")
            continue
        text = visible_text(path)
        if phrase.lower() not in text.lower():
            failures.append(
                f"{rel}: {what} — {phrase!r} is not in the markup once scripts are "
                f"stripped, so it needs JavaScript to appear ({len(text)} chars of text)"
            )
        else:
            print(f"  [PASS] {rel:28s} {what}")

    # Every item page must carry its own reasoning text, not a shell to be filled in.
    thin = []
    for path in pages:
        if "/items/" not in str(path):
            continue
        chars = len(visible_text(path))
        if chars < 800:
            thin.append(f"{path.relative_to(OUT)} ({chars} chars)")
    if thin:
        failures.append(f"item pages rendered thin, so their content is not in the HTML: {thin}")
    else:
        n = sum(1 for p in pages if "/items/" in str(p))
        print(f"  [PASS] {n} item pages carry their trace text in the markup")

    for path in pages:
        markup = re.sub(r"<script.*?</script>", " ", path.read_text(), flags=re.DOTALL)
        for host in FORBIDDEN_IN_MARKUP:
            if host in markup:
                failures.append(f"{path.relative_to(OUT)}: markup references {host}")

    if failures:
        print("\nFE-10 FAIL:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nFE-10: PASS — the export renders from the filesystem with nothing running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
