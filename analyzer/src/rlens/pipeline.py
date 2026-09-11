"""Span trees in, one `ReasoningReport` out — C3.3, the object G1 freezes.

Owner: M1-10.

This is the assembly layer and deliberately nothing else. Every number it writes is
computed somewhere below it — `segment` for the steps, `classify` for the labels,
`checkers` for correctness — and the one thing this module is allowed to do on its own is
arithmetic over those results (shares, counts, ratios). The moment it starts *deciding*
anything, the decision has no test of its own and no owner.

What Month 1 can and cannot fill in
-----------------------------------
The schema accommodates fields Month 2 and Month 3 populate, and this module writes `null`
for every one of them rather than a plausible zero:

| Field | Filled by | Month-1 value |
| --- | --- | --- |
| `validity.escalated` | M2-5 | always `false` — the tier does not exist |
| `consistency` | M2-8 | `null` |
| `measurement_context` | M2-17 | all-null, and it still renders |
| `metrics.est_cost_usd` | M2-10b's price table | `null` |

**A null here is load-bearing.** I3 says every score renders next to its own error bars; a
`measurement_context` of zeros would render as *"kappa 0.0"* — a measured failure — where
the truth is *"not measured yet"*. The UI can tell those apart only if this module refuses
to invent the difference.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import Any

from rlens.checkers import CheckerError, check
from rlens.classify import ClassificationResult, StepRow, classify
from rlens.contracts import NormalizedTrace
from rlens.ingest import otel
from rlens.llm import ProviderError
from rlens.segment import segment
from rlens.versions import (
    ANALYZER_VERSION,
    PROMPT_BUNDLE_VERSION,
    RUNNER_VERSION,
    GenerationPin,
    generation_pin,
)

SCHEMA_PATH = pathlib.Path(__file__).parent / "schemas/reasoning_report.schema.json"
SCHEMA_VERSION = "1.0"

#: The order arms render in. Fixed here rather than taken from the filesystem so a report
#: reads the same everywhere -- the cost contrast that FE-1 features is direct-vs-thinking,
#: and a UI that has to sort the arms itself will eventually sort them differently.
ARM_ORDER = ("direct", "thinking", "react")


def load_schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())
    return data


def validate_report(report: dict[str, Any]) -> None:
    """Raise if the report does not conform. **This function is the G1 freeze mechanism.**

    Not a defensive check: the three committed fixtures validate through here in CI, so a
    schema change that breaks one of them fails a build rather than surfacing in W5 as a
    frontend owner's question.
    """
    import jsonschema

    jsonschema.validate(report, load_schema())


# ------------------------------------------------------------------------ arm assembly
def _pattern_profile(rows: tuple[StepRow, ...]) -> dict[str, float] | None:
    """Share of classified steps per behavior class.

    `None` rather than all-zeros on an unlabelled arm. Zeros would read as "we looked and
    found none of these behaviours", which is a finding; the truth is that nothing looked.
    """
    if not rows:
        return None
    total = len(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.behavior] = counts.get(row.behavior, 0) + 1
    # Every class is present with an explicit 0.0 so a bar chart has five bars rather than
    # however many the model happened to use. An absent CLASS and an absent PROFILE are
    # different statements, and only the second one means "not measured".
    return {
        label: round(counts.get(label, 0) / total, 4)
        for label in (
            "verification",
            "backtracking",
            "subgoal_setting",
            "backward_chaining",
            "linear",
        )
    }


def _soundness_score(rows: tuple[StepRow, ...]) -> float | None:
    """Share of classified steps judged `sound`.

    `unverifiable` counts against it, and that is a choice worth naming: an unverifiable
    step is not a sound one, and a score that treated it as neutral would read highest on
    a trace that asserts everything and derives nothing.
    """
    if not rows:
        return None
    return round(sum(1 for r in rows if r.verdict == "sound") / len(rows), 4)


def build_arm(
    trace: NormalizedTrace,
    classification: ClassificationResult | None,
    *,
    item: dict[str, Any],
    status: str = "ok",
    degraded: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One arm's block of the report.

    `degraded` is an override for the case where there is no `ClassificationResult` to
    read one off -- an analysis call that failed at the transport rather than at the
    model. The arm still carries its steps, because the TRACE is fine; it is the
    annotation that is missing, and those are different failures.
    """
    labels = classification.by_step_id() if classification else {}
    if degraded is None:
        degraded = classification.degraded if classification else None

    steps = []
    for step in trace.steps:
        row = labels.get(step.step_id)
        steps.append(
            {
                "step_id": step.step_id,
                "kind": step.kind,
                "text": step.text,
                "char_range": list(step.char_range) if step.char_range else None,
                # A degraded arm renders its steps with NO behavior and NO validity, which
                # is the whole point of C4.3's parse-failure rule: the text is real and
                # the labels are absent, and the reader can see exactly that.
                "behavior": (
                    {"label": row.behavior, "confidence": row.behavior_confidence} if row else None
                ),
                "validity": (
                    {
                        "verdict": row.verdict,
                        "confidence": row.validity_confidence,
                        "error_type": row.error_type,
                        # M2-5 owns the escalation tier. False here is a fact about this
                        # run, not a placeholder: no step in Month 1 was re-judged.
                        "escalated": False,
                        "rationale": row.rationale or None,
                    }
                    if row
                    else None
                ),
            }
        )

    rows = classification.rows if classification else ()
    usage = trace.usage
    return {
        "strategy": trace.strategy,
        "status": status,
        "trace_quality": trace.trace_quality,
        "final_answer": trace.final_answer,
        "correct": _correct(item, trace.final_answer),
        "steps": steps,
        # M2-8 builds the consistency checker. Null, not a cheerful `entails`.
        "consistency": None,
        "metrics": {
            "output_tokens": usage.output_tokens or None,
            "reasoning_tokens": usage.reasoning_tokens,
            "answer_tokens": usage.answer_tokens,
            "input_tokens": usage.input_tokens or None,
            # M2-10b owns the price table. A cost figure invented here would be the one
            # number on the page nobody could reproduce.
            "est_cost_usd": None,
            "latency_ms": trace.timings.latency_ms,
            "turns": trace.timings.turns,
            "pattern_profile": _pattern_profile(rows),
            "soundness_score": _soundness_score(rows),
            "flagged_step_count": sum(1 for r in rows if r.verdict != "sound") if rows else None,
            "classifier_calls": classification.calls if classification else None,
            "classifier_repairs": classification.repairs if classification else None,
        },
        "degraded": degraded,
        "escalation_capped": False,
        "budget_bound": False,
    }


def _correct(item: dict[str, Any], answer: str) -> bool | None:
    """Three outcomes, not two. **`None` means we could not read the answer.**

    M1-5 paid 1.2 unbudgeted hours for this distinction and it is worth restating: `false`
    asserts the model answered and was wrong. On a trace that never produced a readable
    answer that is a claim about the model which the evidence does not support.
    """
    known = item.get("known_answer")
    if known is None or not answer.strip():
        return None
    try:
        return check(known, answer, item.get("checker", "exact"), item.get("tolerance"))
    except CheckerError:
        return None


# ------------------------------------------------------------------------ the report
def _scoreboard(arms: list[dict[str, Any]]) -> dict[str, Any]:
    """B4 #7's headline for this item — and only what ADR-006 leaves it able to claim.

    ADR-006 measured 0 of 16 items separating the arms on accuracy, so `accuracy_delta_pp`
    is almost always 0. It is computed and kept rather than dropped: **a measured zero is
    a finding**, and a field that disappears when it is uninteresting cannot be used to
    show that it was uninteresting.

    `verdict_line` stays null here. M2-10b owns the wording, and a sentence generated in
    Month 1 would be the kind of claim ADR-006 exists to stop: written before the numbers
    that constrain it.
    """
    by = {arm["strategy"]: arm for arm in arms}
    ratio = None
    direct, thinking = by.get("direct"), by.get("thinking")
    if direct and thinking:
        base = (direct.get("metrics") or {}).get("reasoning_tokens")
        deep = (thinking.get("metrics") or {}).get("reasoning_tokens")
        if base and deep:
            ratio = round(deep / base, 2)
    delta = None
    if direct and thinking and direct["correct"] is not None and thinking["correct"] is not None:
        delta = 100.0 * (int(thinking["correct"]) - int(direct["correct"]))
    return {"verdict_line": None, "cost_of_thought_ratio": ratio, "accuracy_delta_pp": delta}


def build_report(
    item: dict[str, Any],
    arms: list[dict[str, Any]],
    *,
    pin: GenerationPin | None = None,
    analyzer_backend: str | None = None,
    judge_triage_pin: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Assemble the frozen object. Validated before it is returned, never after."""
    pin = pin if pin is not None else generation_pin()
    arms = sorted(arms, key=lambda a: ARM_ORDER.index(a["strategy"]))
    report = {
        "schema_version": SCHEMA_VERSION,
        "item": {
            "id": item["id"],
            "prompt": item["prompt"],
            "tags": list(item.get("tags") or []),
            "known_answer": item.get("known_answer"),
            "checker": item.get("checker"),
            "tolerance": item.get("tolerance"),
            "is_trap": bool(item.get("is_trap", False)),
            "trap_note": item.get("trap_note"),
            "source": item.get("source"),
        },
        "generated_at": generated_at or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "versions": {
            "runner": RUNNER_VERSION,
            "analyzer": ANALYZER_VERSION,
            "prompts": PROMPT_BUNDLE_VERSION,
            "model_pin": pin.fingerprint(),
            "model_pin_fields": {
                "model": pin.model,
                "digest": pin.digest,
                "quantization": pin.quantization,
                "runtime": pin.runtime,
                "temperature": pin.temperature,
                "top_p": pin.top_p,
                "seed": pin.seed,
                "reasoning_effort": pin.reasoning_effort,
            },
            "judge_triage_pin": judge_triage_pin,
            # M2-5's tier. A report carrying escalated steps and a null pin here is not
            # publishable, which is why the field exists before the tier does.
            "judge_escalate_pin": None,
            "analyzer_backend": analyzer_backend,
        },
        "arms": arms,
        "scoreboard": _scoreboard(arms),
        # I3. All-null in Month 1 and it STILL renders: "not yet measured" is a state the
        # UI must have, because it is the state every number is in until M2-17.
        "measurement_context": {
            "classifier_kappa_heldout": None,
            "classifier_kappa_dev": None,
            "majority_class_baseline": None,
            "per_class_f1": None,
            "judge_precision": None,
            "judge_recall": None,
            "consistency_fp_rate": None,
            "n_heldout": None,
            "n_dev": None,
            "calibration_run_id": None,
        },
    }
    validate_report(report)
    return report


# ------------------------------------------------------------------------ the pipeline
def analyze_item(
    item: dict[str, Any],
    spans_dir: pathlib.Path,
    *,
    strategies: tuple[str, ...] = ARM_ORDER,
) -> dict[str, Any]:
    """Read this item's span trees, segment, classify, and assemble the report.

    A missing span tree is skipped rather than failing the report: B6.5 says the other
    arms still render, and that has to be true of an arm that was never run as well as one
    that failed mid-flight.
    """
    import os

    arms = []
    for strategy in strategies:
        path = spans_dir / f"{item['id']}.{strategy}.json"
        if not path.exists():
            continue
        trace = segment(otel.parse(json.loads(path.read_text())))
        # The cassette name is passed ALWAYS, not only in mock mode. `rlens.llm.analyze`
        # decides what to do with it -- replay under MOCK_LLM=1, record under
        # RECORD_CASSETTES=1, ignore otherwise -- so the recorded call and the production
        # call are the same call, taken on the same code path (M1-14).
        prefix = f"classify.{item['id']}.{strategy}"
        try:
            result = classify(trace, item_prompt=item["prompt"], cassette_prefix=prefix)
        except ProviderError as exc:
            # **B6.5: the other arms still render.** `classify` returns a degraded result
            # for a model that answered badly, but RAISES for a transport failure -- a
            # truncation, a deadline, a dead connection. Letting that propagate would lose
            # two good arms to one bad call, which is the opposite of what C4.1's
            # failure handling exists for.
            #
            # **`status` stays `ok`.** The schema is explicit that `failed` means the
            # GENERATION call did not return, and this arm generated fine -- there is a
            # complete trace sitting right here. What failed is a downstream stage, which
            # is precisely what `degraded` means. Marking it `failed` would tell a reader
            # the model never answered, which is a claim about the model that the evidence
            # does not support: the same `unparsed`-vs-`wrong` distinction M1-5 and M1-8
            # each paid for, arriving a third time.
            arms.append(
                build_arm(
                    trace,
                    None,
                    item=item,
                    degraded={
                        "reason": "analysis_unavailable",
                        "affects": ["behavior", "validity"],
                        "detail": f"{type(exc).__name__}: {str(exc)[:300]}",
                    },
                )
            )
            continue
        arms.append(build_arm(trace, result, item=item))
    if not arms:
        raise FileNotFoundError(
            f"no span trees for {item['id']} in {spans_dir}. Run "
            f"`python -m rlens.runner --item {item['id']} --all-arms` or `make spans` first."
        )
    backend = os.environ.get("ANALYZER_BACKEND", "hybrid")
    triage = (
        os.environ.get("MODEL_ANALYZE") if backend == "hybrid" else os.environ.get("LOCAL_MODEL")
    )
    return build_report(item, arms, analyzer_backend=backend, judge_triage_pin=triage or None)
