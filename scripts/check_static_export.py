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

    # ---------------------------------------------------------------- FE-2b
    # **Every state the fixtures can produce must actually appear in the markup.** A
    # component that renders four of five behaviour classes looks correct on the class it
    # is being demoed with, and the fifth is discovered by whoever opens the one trace that
    # has it. The fixtures exist precisely so that is checkable here instead.
    all_items = " ".join(visible_text(p) for p in pages if "/items/" in str(p)).lower()
    states = {
        "verification": "behaviour class",
        "backtracking": "behaviour class",
        "subgoal setting": "behaviour class",
        "backward chaining": "behaviour class",
        "linear": "behaviour class",
        "unsound": "validity verdict",
        "unverifiable": "validity verdict",
        "sound": "validity verdict",
        "unannotated": "a step with no label (degraded arm)",
        "arm failed": "a failed arm",
    }
    missing = [f"{s} ({what})" for s, what in states.items() if s not in all_items]
    if missing:
        failures.append(f"FE-2b — states no fixture renders: {missing}")
    else:
        print(f"  [PASS] all {len(states)} annotated-trace states render across the fixtures")

    # Greyscale: a tag must never be categorisable by colour alone. Each one carries its
    # own text, which is the floor, and the validity tags additionally carry a border
    # shape — asserted here so a later CSS tidy cannot quietly remove it.
    css = (ROOT / "frontend/app/globals.css").read_text()
    for cls, cue in (("tag-v.unsound", "solid"), ("tag-v.unverifiable", "dashed")):
        rule = next((line for line in css.splitlines() if line.startswith(f".{cls} ")), "")
        if cue not in rule:
            failures.append(f"FE-2b — .{cls} lost its {cue} border: greyscale cue is colour-only")
    if not any("FE-2b — .tag-v" in f for f in failures):
        print("  [PASS] validity tags carry a shape cue, not colour alone")

    # ---------------------------------------------------------------- FE-11 (L3)
    # **The replay banner is the one label on this site that cannot be optional.** A
    # planted error rendered without it is a deliberately broken trace presented as a real
    # one, so it is asserted in the EXPORTED MARKUP with every script stripped -- if it
    # lived only in the JS payload, a reader with no JavaScript would get the trace and not
    # the label, which is the exact failure mode inverted.
    replay_pages = sorted((OUT / "items").glob("SE-*/index.html"))
    if not replay_pages:
        print("  [SKIP] no replay pages exported -- run `make replay-reports`")
    else:
        missing = []
        for path in replay_pages:
            markup = re.sub(r"<script.*?</script>", " ", path.read_text(), flags=re.DOTALL)
            if "deliberately planted" not in markup:
                missing.append(path.parent.name)
        if missing:
            failures.append(
                f"FE-11 -- {len(missing)} replay page(s) render no planted-error banner in "
                f"script-free markup: {missing[:4]}"
            )
        else:
            print(f"  [PASS] all {len(replay_pages)} replay pages carry the planted-error banner")
        # Non-dismissible is a property of there being nothing to press, so it is checked
        # as the absence of an affordance rather than as the presence of a word.
        dismissible = [
            p.parent.name
            for p in replay_pages
            if re.search(r"notice planted[^\"]*\"[^<]*<button", p.read_text())
        ]
        if dismissible:
            failures.append(
                f"FE-11 -- the planted-error banner gained a dismiss control: {dismissible}"
            )
        else:
            print("  [PASS] the planted-error banner has no dismiss control")

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
