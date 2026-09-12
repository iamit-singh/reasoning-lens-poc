#!/usr/bin/env python3
"""M2-6 — the seeded-error harness. Judge recall, per error type, with the correct-step rule.

    make seeded-errors               # all 10 cases + the baselines
    make seeded-errors ARGS="--dry-run"   # patch and diff only, no model, no spend

B4 #3. Ten hand-written mutations (Appendix B) are applied to five **known-good** traces —
traces that answered correctly before anything was changed — and the judge is asked whether
it flags the step that was broken.

The correct-step rule, and why it is the whole measurement
---------------------------------------------------------
**A hit requires flagging the step that was mutated.** Not "the trace was flagged
somewhere". A judge that flags three steps out of five on every trace will catch every
seeded error by accident, and its recall will read beautifully while it is useless: a
reviewer following that flag lands on a sound step and loses trust in the instrument.

So this harness records three numbers per case rather than one, because they answer
different questions:

* **hit** — the mutated step was flagged. This is the numerator of B4 #3.
* **collateral** — how many *other* steps were flagged in the same run. A hit with three
  collateral flags is a worse result than a hit with none, and folding them together hides
  that.
* **baseline flags** — the same trace, unmutated, run through the same judge. This is the
  false-flag rate on known-good text, and it is the denominator of honesty: a judge whose
  baseline flags every second step has not "caught" anything by flagging one more.

Why the mutation is applied AFTER segmentation
----------------------------------------------
The patch edits `Step.text` on an already-segmented trace, never the raw span. `step_id`
embeds the segmenter's ordinal, so re-segmenting mutated text could renumber the steps and
`expected_flag_step_id` would point at different text than the one that was broken — the
Hazard-1 failure, arriving through a side door. Editing after segmentation keeps every id
identical to the known-good run by construction, which is also what makes the baseline
comparison a comparison.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "analyzer/src"))

from rlens.classify import classify
from rlens.ingest import otel
from rlens.llm import ProviderError
from rlens.runner.run import load_item
from rlens.segment import segment
from rlens.versions import PROMPT_BUNDLE_VERSION

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = ROOT / "calibration/seeded"
OUT = ROOT / "docs/spikes/M2-6-raw"


def load_cases(only: str = "") -> list[dict]:
    cases = [json.loads(p.read_text()) for p in sorted(CASES.glob("SE-*.json"))]
    return [c for c in cases if not only or only in c["case_id"]]


def apply_patch(trace, case: dict):
    """Return (mutated_trace, mutated_step_id). Raises if the patch did not apply.

    **A patch that does not match is a hard error, never a skip.** A silently unapplied
    patch produces a run over unmutated text, the judge correctly flags nothing, and the
    result is recorded as a recall miss — a measurement that says the judge failed when
    the harness did.
    """
    ordinal = case["mutated_step_ordinal"]
    find = case["patch"]["find"]
    replace = case["patch"]["replace"]

    steps = [s.model_copy(deep=True) for s in trace.steps]
    if ordinal >= len(steps):
        raise SystemExit(f"{case['case_id']}: step {ordinal} does not exist ({len(steps)} steps)")
    target = steps[ordinal]
    if find not in target.text:
        raise SystemExit(
            f"{case['case_id']}: patch did not apply to step {ordinal}.\n"
            f"  looking for: {find!r}\n"
            f"  step text:   {target.text[:200]!r}\n"
            f"The trace changed under the case. Re-author the case against the current "
            f"text rather than loosening the match -- a fuzzy patch mutates something "
            f"other than what the case documents."
        )
    steps[ordinal] = target.model_copy(update={"text": target.text.replace(find, replace, 1)})
    return trace.model_copy(update={"steps": steps}), target.step_id


def flagged_ids(result) -> set[str]:
    """Step ids the judge did not call `sound`.

    `unverifiable` counts as flagged. The seeded step IS defective, and whether a defect is
    "wrong" or "uncheckable" is M2-2's adjudication; for recall, a judge that stopped and
    said "I cannot verify this" did not miss it.
    """
    return {r.step_id for r in result.rows if r.verdict != "sound"}


def run_case(case: dict, *, baselines: dict) -> dict:
    span = ROOT / case["base_span_path"]
    item_id = span.name.split(".")[0]
    item = load_item(item_id)
    clean = segment(otel.parse(json.loads(span.read_text())))
    mutated, step_id = apply_patch(clean, case)

    # One baseline per TRACE, not per case: three cases share mb-06.thinking, and running
    # the unmutated trace three times would triple the spend to measure the same thing.
    key = case["base_span_path"]
    if key not in baselines:
        t0 = time.time()
        base = classify(clean, item_prompt=item["prompt"])
        baselines[key] = {
            "flagged": sorted(flagged_ids(base)),
            "n_steps": len(clean.steps),
            "degraded": base.degraded,
            "secs": round(time.time() - t0, 1),
        }
    base = baselines[key]

    t0 = time.time()
    try:
        result = classify(mutated, item_prompt=item["prompt"])
    except ProviderError as exc:
        return {**_meta(case, step_id, base), "error": str(exc)[:200], "hit": None}

    if result.degraded:
        # A degraded arm has no labels at all, so it is neither a hit nor a miss. Counting
        # it as a miss would blame the judge for a parse failure.
        return {**_meta(case, step_id, base), "degraded": result.degraded, "hit": None}

    flags = flagged_ids(result)
    hit = step_id in flags
    row = {r.step_id: r for r in result.rows}.get(step_id)
    return {
        **_meta(case, step_id, base),
        "hit": hit,
        "verdict": row.verdict if row else None,
        "error_type": row.error_type if row else None,
        "validity_confidence": row.validity_confidence if row else None,
        "rationale": (row.rationale if row else "")[:160],
        # Collateral excludes steps the baseline already flagged: those are the judge's
        # standing opinion about this trace, not damage caused by the mutation.
        "collateral": sorted(flags - {step_id} - set(base["flagged"])),
        "flagged_all": sorted(flags),
        "secs": round(time.time() - t0, 1),
    }


def _meta(case: dict, step_id: str, base: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "mutation_type": case["mutation_type"],
        "expected_error_type": case["expected_error_type"],
        "trace": case["base_span_path"].split("/")[-1].removesuffix(".json"),
        "expected_flag_step_id": step_id,
        "baseline_flagged": base["flagged"],
        "baseline_n_steps": base["n_steps"],
    }


def dry_run(cases: list[dict]) -> int:
    """Apply every patch and print the diff. No model, no network, no spend.

    Worth having as its own mode: it is how a case is authored and how a case that has
    rotted against a changed trace is found, and neither of those should cost anything.
    """
    for case in cases:
        span = ROOT / case["base_span_path"]
        clean = segment(otel.parse(json.loads(span.read_text())))
        mutated, step_id = apply_patch(clean, case)
        print(f"\n=== {case['case_id']} · {case['mutation_type']} -> {case['expected_error_type']}")
        print(f"    {step_id}")
        print(f"  - {clean.steps[case['mutated_step_ordinal']].text[:220]}")
        print(f"  + {mutated.steps[case['mutated_step_ordinal']].text[:220]}")
    print(f"\n{len(cases)} cases, all patches applied cleanly.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="", help="substring filter on case_id")
    ap.add_argument("--dry-run", action="store_true", help="patch and diff only; no spend")
    args = ap.parse_args(argv)

    cases = load_cases(args.only)
    if not cases:
        print(f"no cases under {CASES}", file=sys.stderr)
        return 2
    if args.dry_run:
        return dry_run(cases)

    print(f"M2-6: {len(cases)} seeded errors · bundle {PROMPT_BUNDLE_VERSION}")
    baselines: dict[str, dict] = {}
    rows = []
    for case in cases:
        row = run_case(case, baselines=baselines)
        rows.append(row)
        mark = "HIT " if row.get("hit") else ("----" if row.get("hit") is None else "MISS")
        extra = f" +{len(row.get('collateral', []))} collateral" if row.get("collateral") else ""
        print(
            f"  [{mark}] {row['case_id']} {row['mutation_type']:24s} "
            f"{row['trace']:18s} verdict={row.get('verdict')}{extra}"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "m2-6-seeded.json").write_text(
        json.dumps(
            {
                "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
                "baselines": baselines,
                "cases": rows,
            },
            indent=2,
        )
        + "\n"
    )

    graded = [r for r in rows if r.get("hit") is not None]
    hits = [r for r in graded if r["hit"]]
    print(f"\n{'=' * 72}\nB4 #3 — judge recall on seeded errors\n{'=' * 72}")
    print(
        f"  recall           {len(hits)}/{len(graded)}"
        f"  ({100.0 * len(hits) / len(graded) if graded else 0:.0f}%)   target: >= 70%"
    )
    ungraded = len(rows) - len(graded)
    if ungraded:
        print(f"  ungraded         {ungraded} (degraded or provider error — not counted as misses)")

    print("\n  per type (n is small on purpose — Appendix B is 10 cases, not a sample):")
    by_type: dict[str, list] = collections.defaultdict(list)
    for r in graded:
        by_type[r["expected_error_type"]].append(r)
    for etype, group in sorted(by_type.items()):
        got = sum(1 for r in group if r["hit"])
        named = sum(1 for r in group if r["hit"] and r.get("error_type") == etype)
        print(f"    {etype:22s} {got}/{len(group)} caught · {named}/{len(group)} named correctly")

    base_flags = sum(len(b["flagged"]) for b in baselines.values())
    base_steps = sum(b["n_steps"] for b in baselines.values())
    print(
        f"\n  known-good baseline   {base_flags} flags over {base_steps} steps in "
        f"{len(baselines)} traces ({100.0 * base_flags / base_steps if base_steps else 0:.1f}%)"
    )
    print("    A judge that flags freely catches seeded errors by accident. This is the")
    print("    number that says whether the recall above was earned (M2-7 formalises it).")
    collateral = sum(len(r.get("collateral", [])) for r in graded)
    print(f"  collateral flags      {collateral} across {len(graded)} runs")
    print(f"\n  record: {(OUT / 'm2-6-seeded.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
