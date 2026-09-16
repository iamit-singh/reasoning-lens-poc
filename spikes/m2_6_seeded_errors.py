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

from rlens import judge
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


def escalated_rows(result, trace, *, item_prompt: str):
    """Apply M2-5's tier to a triage result, returning (rows, outcome) or (rows, None).

    **This harness measured recall for three runs with no escalation in it at all**, and
    setting `ESCALATION_ENABLED=1` changed nothing because nothing here read the flag. A
    "recall delta over triage-alone" computed from that would have compared triage against
    triage and published the difference as the two-tier design's justification -- the same
    shape as the consistency checker that was built, tested and never called.

    So the tier is applied explicitly here, and the OUTCOME is returned so the record can
    say how many steps were selected and how many verdicts actually moved. A delta of zero
    is a publishable finding (t9); a delta of zero because the tier never ran is not a
    finding at all.
    """
    if not judge.enabled():
        return result.rows, None
    outcome = judge.escalate(list(result.rows), list(trace.steps), item_prompt=item_prompt)
    if not outcome.rows:
        return result.rows, outcome
    merged = []
    for row in result.rows:
        up = outcome.rows.get(row.step_id)
        merged.append(row.model_copy(update={"verdict": up.verdict}) if up else row)
    return merged, outcome


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
        base_rows, base_esc = escalated_rows(base, clean, item_prompt=item["prompt"])
        baselines[key] = {
            "flagged": sorted({r.step_id for r in base_rows if r.verdict != "sound"}),
            "flagged_triage_only": sorted(flagged_ids(base)),
            "n_steps": len(clean.steps),
            "degraded": base.degraded,
            "escalation": _esc_record(base_esc),
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

    triage_flags = flagged_ids(result)
    rows_after, outcome = escalated_rows(result, mutated, item_prompt=item["prompt"])
    flags = {r.step_id for r in rows_after if r.verdict != "sound"}
    hit = step_id in flags
    # **Both halves recorded, always.** The delta the two-tier design is justified by is
    # `hit` minus `hit_triage_only`, and it can only be computed if the triage-alone answer
    # survives into the record rather than being overwritten by the escalated one.
    hit_triage_only = step_id in triage_flags
    row = {r.step_id: r for r in result.rows}.get(step_id)
    after = {r.step_id: r for r in rows_after}.get(step_id)
    return {
        **_meta(case, step_id, base),
        "hit": hit,
        # `verdict` is the TRIAGE verdict and `verdict_after_escalation` is what the step
        # ended up with. Keeping only one of them was a real defect: the run that found the
        # negative escalation delta printed SE-06 as "[MISS] ... verdict=unsound", because
        # the hit came from the escalated rows and the verdict column came from the triage
        # ones. A row that reads MISS next to `unsound` is not a typo a reader can resolve.
        "verdict": row.verdict if row else None,
        "verdict_after_escalation": after.verdict if after else None,
        "error_type": row.error_type if row else None,
        "validity_confidence": row.validity_confidence if row else None,
        "rationale": (row.rationale if row else "")[:160],
        # Collateral excludes steps the baseline already flagged: those are the judge's
        # standing opinion about this trace, not damage caused by the mutation.
        "collateral": sorted(flags - {step_id} - set(base["flagged"])),
        "flagged_all": sorted(flags),
        "hit_triage_only": hit_triage_only,
        "flagged_triage_only": sorted(triage_flags),
        "escalation": _esc_record(outcome),
        "secs": round(time.time() - t0, 1),
    }


def _verdict_cell(row: dict) -> str:
    """The verdict as it ended up, and the triage one too when escalation moved it.

    Printing only the triage verdict made a MISS sit next to `unsound` on any case the
    tier overturned, which is unreadable and was how the escalation regression first
    showed up as "that line is wrong" rather than as a finding.
    """
    before, after = row.get("verdict"), row.get("verdict_after_escalation")
    if after is None or after == before:
        return str(before)
    return f"{before}->{after}"


def _esc_record(outcome) -> dict | None:
    """What the tier actually did, or None when it did not run.

    None and `{"selected": 0}` are different states and both must be distinguishable in the
    record: the first means escalation was off, the second means it was on and the policy
    chose nothing. Reporting a zero delta without saying which one produced it is how "the
    tier did not earn its tokens" and "the tier never ran" become the same sentence.
    """
    if outcome is None:
        return None
    return {
        "selected": len(outcome.selected),
        "capped": outcome.capped,
        "rate": round(outcome.rate, 4),
        "verdicts_changed": list(outcome.changed),
        "calls": outcome.calls,
        "note": outcome.note or None,
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
            f"{row['trace']:18s} verdict={_verdict_cell(row)}{extra}"
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
    # ---- M2-5's DoD: the delta the two-tier design is justified by.
    esc_rows = [r for r in graded if r.get("escalation") is not None]
    if not esc_rows:
        print(
            "  escalation       NOT RUN (ESCALATION_ENABLED off) — so the recall above is\n"
            "                   TRIAGE-ALONE and no delta is computable from this run."
        )
    else:
        triage_hits = [r for r in graded if r.get("hit_triage_only")]
        selected = sum(r["escalation"]["selected"] for r in esc_rows)
        changed = sum(len(r["escalation"]["verdicts_changed"]) for r in esc_rows)
        delta = len(hits) - len(triage_hits)
        print(
            f"  triage alone     {len(triage_hits)}/{len(graded)}"
            f"  ({100.0 * len(triage_hits) / len(graded) if graded else 0:.0f}%)"
        )
        print(
            f"  ESCALATION DELTA {delta:+d} case(s)   "
            f"{selected} step(s) selected, {changed} verdict(s) changed, "
            f"{sum(r['escalation']['calls'] for r in esc_rows)} extra call(s)"
        )
        if delta == 0:
            print(
                "                   t9's condition. Its pre-decided action is PUBLISH IT:\n"
                "                   escalation did not earn its tokens on this workload,\n"
                "                   and that is a finding plus a Month-3 simplification.\n"
                "                   Note WHICH zero this is: the tier RAN and changed "
                f"{changed} verdict(s)."
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
