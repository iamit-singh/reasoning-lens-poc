#!/usr/bin/env python3
"""Fail the build when a rendered report's prompt bundle is not the shipping one — E12-D2.

    make bundle-check

WHY THIS EXISTS, AND WHY A SENTENCE WAS NOT ENOUGH
--------------------------------------------------
The calibration page states that every figure belongs to one model pin and one prompt
bundle and **expires if either changes**. On 23 Sep two naive testers found, independently,
that the site was already serving two bundles while saying that: `mb-*` pages rendered
`e8952d4d3c` and every `SE-*` page rendered `97667881c7`. One of them spent their only
recorded confusion trying to work out whether it was a deliberate distinction or drift
nobody had noticed, and asked for exactly this:

    "I would want a build-time assertion that fails the build rather than a sentence asking
     the reader to check."

An expiry rule that nothing enforces is not a rule. This is the enforcement.

WHAT IT DOES *NOT* CLAIM
------------------------
The drift is in the rendered artifacts, **not in the published measurements.** M2-6's raw
evidence (`docs/spikes/M2-6-raw/m2-6-seeded.json`) is recorded at the current bundle, so
judge recall 0.80 is correctly attributed; the seeded *reports* are leftovers from an
earlier judging run that the frontend kept rendering. Re-judging them costs real model
calls and would be a **measurement**, not a rendering fix, so it is not done here and not
done silently.

DECLARED IS NOT THE SAME AS CLEAN
---------------------------------
A second vintage may ship — some artifacts are expensive to regenerate — but it may not
ship *silently*. Anything not at the shipping bundle must be listed in DECLARED below with
a reason, and the page must say so. That converts an invisible drift into a recorded one,
which is the whole difference this check is trying to make.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))
from rlens.versions import PROMPT_BUNDLE_VERSION

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Artifacts knowingly shipped at an older bundle, each with the reason it was not
#: regenerated. A path here is ALLOWED TO DIFFER AND REQUIRED TO BE LABELLED -- the
#: frontend renders a vintage banner for exactly these. Removing a path from this list
#: without regenerating it turns the build red, which is the point.
DECLARED = {
    "calibration/seeded/reports": (
        "Seeded-error reports judged at 97667881c779. Re-judging is 10 live analysis "
        "calls and would be a re-measurement of M2-6, not a rebuild -- so they ship "
        "labelled rather than silently refreshed. Recall 0.80 is unaffected: its raw "
        "evidence in docs/spikes/M2-6-raw/ was recorded at the shipping bundle."
    ),
}

SCAN = ["out/reports", "calibration/seeded/reports"]


def _bundle(doc: dict) -> str | None:
    return doc.get("prompt_bundle_version") or (doc.get("versions") or {}).get("prompts")


def main() -> int:
    undeclared: list[tuple[str, str]] = []
    declared: list[tuple[str, str]] = []
    clean = 0

    for rel in SCAN:
        d = ROOT / rel
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.report.json")):
            got = _bundle(json.loads(f.read_text()))
            name = f"{rel}/{f.name}"
            if got == PROMPT_BUNDLE_VERSION:
                clean += 1
            elif rel in DECLARED:
                declared.append((name, got or "absent"))
            else:
                undeclared.append((name, got or "absent"))

    if not (ROOT / "out/reports").is_dir() or not any((ROOT / "out/reports").glob("*.report.json")):
        # out/ is gitignored. On a clean checkout this used to scan only the ten committed
        # seeded reports and pass -- a green check on everything except what ships.
        print("no reports under out/reports -- run `make demo-data` first", file=sys.stderr)
        return 2

    print(f"shipping prompt bundle: {PROMPT_BUNDLE_VERSION}")
    print(f"  at the shipping bundle : {clean}")
    print(f"  declared older vintage : {len(declared)}")

    for path, reason in DECLARED.items():
        if any(n.startswith(path) for n, _ in declared):
            print(f"    {path}/ -- {reason}")

    if undeclared:
        print(
            f"\nUNDECLARED BUNDLE DRIFT: {len(undeclared)} report(s) render a prompt bundle "
            f"that is not the shipping one and are not declared.",
            file=sys.stderr,
        )
        print(
            "The calibration page states every figure expires if the bundle changes. "
            "Serving these alongside it makes that statement false.",
            file=sys.stderr,
        )
        for name, got in undeclared:
            print(f"  {name}: {got}", file=sys.stderr)
        print(
            "\nEither regenerate them at the shipping bundle, or add them to DECLARED in "
            "this file with the reason they ship stale -- and label them in the UI.",
            file=sys.stderr,
        )
        return 1

    print("\nbundle-check: OK -- no undeclared vintage on any rendered report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
