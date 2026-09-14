#!/usr/bin/env python3
"""M2-6's last clause — the mutated reports the replay surface serves. **COSTS SPEND.**

    make replay-reports                    # all 10 cases
    make replay-reports ARGS="--case SE-01"
    make replay-reports ARGS="--dry-run"   # patch, diff and report shape only, no model

M2-6 measured judge recall and stopped. Its card has one more sentence: *"the mutated
reports serve the demo's replay surface from cache with a persistent 'Illustrative: an
error was deliberately planted in this trace' banner — no live call, so it survives a
provider outage. **Commit them.**"* They were never committed. This is that.

Why the demo wants them at all
------------------------------
C4.8: the realistic stage failure is not a wrong answer, it is **no answer** — a provider
outage, a dead network, a laptop that cannot reach anything. A replay entry is a trace that
needs none of those, and it is the one surface that can *demonstrate the instrument
catching something* without asking a model anything at the time.

**The third provenance category, and why it needs saying**
----------------------------------------------------------
This project already distinguishes **measured** reports from **authored** fixtures, and
`Provenance` renders the difference loudly. A mutated report is neither:

* it is **not authored** — a real model really produced these labels, on the pinned tier;
* it is **not a clean measurement** — the text it judged was **deliberately edited by us**.

So it must never be served through the same path as `out/reports`. These land in their own
directory and are reached only through `/api/replay/{case_id}`, which already wraps its
payload in `{"illustrative": true, ...}`. **The flag belongs to the data, not to the page
that happens to render it** — a report travels into a download, a cache and possibly a
screenshot, and the banner has to travel with it.

The schema is not touched. C3.3's freeze is additive-only and this needs nothing added:
the marker lives in the endpoint's wrapper, which already exists.

Cassettes, so this is not a one-way spend
-----------------------------------------
Each mutated classification is recorded under `replay.<case>` so the whole set regenerates
offline with `MOCK_LLM=1`. Without that, a prompt-bundle change would make these
unreproducible except by spending again — and an artifact nobody can rebuild is one nobody
can check.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))
sys.path.insert(0, str(ROOT / "spikes"))

from m2_6_seeded_errors import apply_patch, load_cases  # noqa: E402
from rlens.classify import classify  # noqa: E402
from rlens.ingest import otel  # noqa: E402
from rlens.llm import ProviderError  # noqa: E402
from rlens.pipeline import build_arm, build_report, validate_report  # noqa: E402
from rlens.runner.run import load_item  # noqa: E402
from rlens.segment import segment  # noqa: E402
from rlens.versions import PROMPT_BUNDLE_VERSION  # noqa: E402

OUT = ROOT / "calibration/seeded/reports"


def build_one(case: dict, *, dry_run: bool) -> dict | None:
    case_id = case["case_id"]
    span = ROOT / case["base_span_path"]
    if not span.exists():
        raise SystemExit(f"{case_id}: no span tree at {span}. Run `make spans` first.")

    item_id, strategy = span.name.split(".")[0], span.name.split(".")[1]
    item = load_item(item_id)
    clean = segment(otel.parse(json.loads(span.read_text())))
    mutated, mutated_step_id = apply_patch(clean, case)

    if dry_run:
        before = clean.steps[case["mutated_step_ordinal"]].text
        after = mutated.steps[case["mutated_step_ordinal"]].text
        print(f"  {case_id}  {item_id}.{strategy}  step {mutated_step_id}")
        print(f"      before: {before[:110]}")
        print(f"      after:  {after[:110]}")
        return None

    started = time.time()
    try:
        result = classify(mutated, item_prompt=item["prompt"], cassette_prefix=f"replay.{case_id}")
    except ProviderError as exc:
        print(f"  {case_id}: FAILED {type(exc).__name__}: {str(exc)[:140]}")
        return None

    arm = build_arm(mutated, result, item=item)
    report = build_report(item, [arm])
    # Validated here rather than trusted: these are served to a browser and downloaded,
    # and a replay report that does not conform is a broken page during the one demo path
    # that is supposed to work when nothing else does.
    validate_report(report)

    flagged = [
        s["step_id"]
        for s in arm["steps"]
        if (s.get("validity") or {}).get("verdict") not in (None, "sound")
    ]
    caught = mutated_step_id in flagged
    payload = {
        "_README": (
            "M2-6's mutated report, for the replay surface. The TEXT WAS DELIBERATELY "
            "EDITED before the judge saw it -- this is neither an authored fixture nor a "
            "clean measurement, and it must only ever be served through "
            "/api/replay/{case_id}, which marks it illustrative. Rebuild offline with "
            "MOCK_LLM=1 make replay-reports."
        ),
        "case_id": case_id,
        "mutation_type": case["mutation_type"],
        "mutated_step_id": mutated_step_id,
        "expected_error_type": case.get("expected_error_type"),
        "judge_flagged_the_mutated_step": caught,
        "judge_flagged_steps": flagged,
        "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "report": report,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{case_id}.report.json").write_text(json.dumps(payload, indent=2) + "\n")
    mark = "caught" if caught else "MISSED"
    print(
        f"  {case_id}  {item_id}.{strategy}  {len(arm['steps'])} steps  "
        f"{mark}  ({len(flagged)} flagged) [{time.time() - started:.0f}s]"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="", help="limit to cases containing this string")
    ap.add_argument("--dry-run", action="store_true", help="patch and diff only, no model")
    args = ap.parse_args(argv)

    replaying = os.environ.get("MOCK_LLM") == "1"
    if not args.dry_run and replaying:
        print(
            "MOCK_LLM=1 -- replaying existing cassettes rather than building. That is the "
            "correct way to REBUILD these offline, so this is allowed; pass --dry-run if "
            "you only wanted the diff.",
            file=sys.stderr,
        )
    if not args.dry_run and not replaying:
        # **Without this the offline rebuild is a claim rather than a fact**, and the
        # docstring above says these regenerate with MOCK_LLM=1. The first version omitted
        # it, the docstring was wrong, and `make replay-reports REPLAY_MOCK=1` found out --
        # which is the fifth time in this project that a capability was asserted in prose
        # and only became true once something ran it.
        os.environ["RECORD_CASSETTES"] = "1"

    cases = load_cases(args.case)
    if not cases:
        print(f"no cases matching {args.case!r}", file=sys.stderr)
        return 2

    print(f"building {len(cases)} replay report(s) · bundle {PROMPT_BUNDLE_VERSION}")
    built = [c for c in (build_one(case, dry_run=args.dry_run) for case in cases) if c]
    if args.dry_run:
        return 0

    caught = sum(1 for b in built if b["judge_flagged_the_mutated_step"])
    print(f"\n{len(built)} of {len(cases)} built -> {OUT}")
    print(f"  judge caught the planted step in {caught} of {len(built)}")
    print(
        "\nThese are NOT clean measurements -- the text was edited before the judge saw it.\n"
        "Serve them only through /api/replay/{case_id}, which marks them illustrative."
    )
    return 0 if len(built) == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
