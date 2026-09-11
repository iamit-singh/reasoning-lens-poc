#!/usr/bin/env python3
"""M1-14 — record the provider responses that make `MOCK_LLM=1` replay the whole pipeline.

    make record-cassettes              # the analysis tier, once per prompt-bundle version
    make record-cassettes ARGS="--generation"   # re-record generation too (needs the GPU)

Three claims elsewhere in the plan assume these already exist, and none of them is true
until they do: the frontend develops against fixtures with zero Lead dependency from W5;
CI's integration-mock job runs on every PR with no LLM calls; local dev is cost-free. All
three start mattering in W5, which is why a 0.5 h recording task sits on the Month-1 board.

Two tiers, recorded differently, and the difference is not cosmetic
------------------------------------------------------------------
* **Generation** (local, the three arms) is recorded by the runner and is keyed by
  `{item}.{strategy}`. It is invalidated by a change to the arm construction, which is what
  `RUNNER_VERSION` names. 49 of these were recorded by M1-7 and are already committed.
* **Analysis** (the classifier) is recorded by running the ordinary pipeline with
  `RECORD_CASSETTES=1`, so the captured call is taken on the *production* code path rather
  than by a harness that re-issues something similar. Each cassette carries the sha of the
  request that produced it and replay refuses a mismatch, which is what "keyed by a hash of
  the request" buys without making the directory unreadable.

**Why the digest matters more than it looks.** A prompt edit changes
`PROMPT_BUNDLE_VERSION`, and a stale cassette would otherwise replay the OLD prompt's
answer under the NEW prompt's version — a green CI run asserting behaviour that no longer
exists. The mismatch check turns that into a loud failure naming the fix.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analyzer/src"))

from rlens.llm import CASSETTE_DIR, ProviderError  # noqa: E402
from rlens.pipeline import analyze_item  # noqa: E402
from rlens.runner.run import load_item  # noqa: E402
from rlens.versions import PROMPT_BUNDLE_VERSION  # noqa: E402

SPANS = ROOT / "out/spans"
MANIFEST = CASSETTE_DIR / "MANIFEST.json"


def record_generation(item_ids: list[str]) -> int:
    """Re-run the three arms against the served model. **Needs the GPU and minutes.**

    Separated behind a flag because it is the expensive half and is invalidated by
    different things: the analysis cassettes go stale when a prompt changes, these go
    stale when the arms or the pin change.
    """
    failures = 0
    for item_id in item_ids:
        print(f"  generation {item_id} ...", flush=True)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "rlens.runner",
                "--item",
                item_id,
                "--all-arms",
                "--out",
                str(SPANS),
            ],
            cwd=ROOT / "analyzer",
            env={**os.environ, "MOCK_LLM": "0", "PYTHONPATH": str(ROOT / "analyzer/src")},
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"    FAILED: {proc.stderr.strip()[:200]}")
            failures += 1
    return failures


def record_analysis(item_ids: list[str]) -> int:
    """Run the ordinary pipeline live with recording on."""
    failures = 0
    for item_id in item_ids:
        started = time.time()
        try:
            item = load_item(item_id)
            report = analyze_item(item, SPANS)
        except (ProviderError, FileNotFoundError, KeyError) as exc:
            print(f"  {item_id}: FAILED {type(exc).__name__}: {str(exc)[:160]}")
            failures += 1
            continue
        degraded = [a["strategy"] for a in report["arms"] if a.get("degraded")]
        note = f"  degraded: {degraded}" if degraded else ""
        print(f"  {item_id}: {len(report['arms'])} arms [{time.time() - started:.0f}s]{note}")
    return failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generation", action="store_true", help="also re-record the three arms")
    ap.add_argument("--item", action="append", default=[], help="limit to these item ids")
    args = ap.parse_args(argv)

    if os.environ.get("MOCK_LLM") == "1":
        # Recording under MOCK_LLM=1 would "record" the cassettes back onto themselves and
        # report success. `.env` ships with MOCK_LLM=1 as the local default, so this is the
        # likely mistake, not a far-fetched one.
        print(
            "MOCK_LLM=1 is set. Recording would replay the existing cassettes and write "
            "them back unchanged. Run with MOCK_LLM=0.",
            file=sys.stderr,
        )
        return 2
    if not SPANS.is_dir():
        print(f"no span trees at {SPANS}. Run `make spans` first.", file=sys.stderr)
        return 2

    item_ids = args.item or sorted({p.name.split(".")[0] for p in SPANS.glob("*.json")})
    print(f"recording cassettes for {len(item_ids)} items · bundle {PROMPT_BUNDLE_VERSION}")

    os.environ["RECORD_CASSETTES"] = "1"
    failures = 0
    if args.generation:
        failures += record_generation(item_ids)
    failures += record_analysis(item_ids)

    analysis = sorted(p.name for p in CASSETTE_DIR.glob("classify.*.json"))
    generation = sorted(
        p.name
        for p in CASSETTE_DIR.glob("*.json")
        if not p.name.startswith(("classify.", "MANIFEST"))
    )
    MANIFEST.write_text(
        json.dumps(
            {
                "_README": (
                    "Written by scripts/record_cassettes.py (M1-14). The prompt bundle "
                    "version is the thing analysis cassettes are keyed to: a prompt edit "
                    "changes it, and every analysis cassette recorded under the old one is "
                    "stale. Each cassette also carries the sha of its own request and "
                    "replay refuses a mismatch, so a stale cassette fails loudly instead "
                    "of replaying the wrong prompt's answer under the new prompt's version."
                ),
                "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
                "analyzer_backend": os.environ.get("ANALYZER_BACKEND", "hybrid"),
                "model_analyze": os.environ.get("MODEL_ANALYZE", ""),
                "local_model": os.environ.get("LOCAL_MODEL", ""),
                "counts": {"generation": len(generation), "analysis": len(analysis)},
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n{len(generation)} generation + {len(analysis)} analysis cassettes · {MANIFEST}")
    if failures:
        print(f"{failures} items failed to record", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
