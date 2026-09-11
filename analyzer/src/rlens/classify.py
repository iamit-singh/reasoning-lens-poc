"""Batched behavior classification + triage judge -- one call per strategy (C4.3).

Owner: M1-9.

What v0 is
----------
The **merged** behavior + triage call. One request per strategy carries the item prompt,
the numbered steps and the final answer, and returns strict JSON with one row per
`step_id`. Merging the two questions into one call is what makes C11's latency budget and
B7.2's token model work; it is not a shortcut.

What v0 is **not** is a tuned prompt. Tuning against measured kappa is M2-3 -- time-boxed,
dev set only, with a changelog. A prompt tuned in W4 against eyeballed output arrives at
Month 2 already fitted to one person's intuitions with nothing to show a reviewer.

Three inheritances from S3, which measured all of this rather than assuming it
-----------------------------------------------------------------------------
1. **Chunk with a cap; do not send a whole trace.** C4.3 says "one call per strategy" and
   S3 measured what that means in practice: traces run from 2 to 141 steps, bimodally.
   `25` is not a batch size, it is a cap -- comfortably above 40 of 42 traces and far
   below the other two. So a trace is split into runs of at most `CLASSIFY_CHUNK_SIZE`
   and the rows are stitched back together on `step_id`.
2. **Low reasoning effort, and an explicit output cap asserted from the output.** Both live
   in `rlens.llm.analyze`, which raises rather than returning a truncated response.
3. **Missing or extra `step_id`s are a parse failure.** Not something to patch up.

The rule in 3 deserves its own paragraph, because the instinct it forbids is a strong one
----------------------------------------------------------------------------------------
When a model returns 24 rows for 25 steps, the tempting repair is to fill the missing one
with `linear` -- it is the majority class, the row is probably unremarkable, and the report
renders. **That instinct manufactures label data.** The fabricated row then flows into the
pattern profile, into the soundness score, and -- if the step is ever sampled -- into the
kappa denominator as though a classifier had produced it. This PoC can survive a low kappa.
It cannot survive publishing numbers computed over rows nobody generated.

So the failure path is: validate -> one repair retry with the validation error appended ->
mark the strategy `degraded: {"reason": "classifier_parse_failure"}` and render it
**unannotated**. A trace with no labels is a visibly incomplete report. A trace with
invented labels is a wrong report that looks complete, and the second is far worse.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from rlens.contracts import RATIONALE_MAX, NormalizedTrace, Step, StepRow
from rlens.llm import AnalysisResult, analyze

_PROMPT = Path(__file__).parent / "prompts" / "classify_and_triage.md"


class ClassifierParseFailure(RuntimeError):
    """Both attempts produced something that is not a conforming set of rows.

    Carries the reason text so the `degraded` block can name it. The caller does not catch
    this to retry; it catches it to render the trace unannotated.
    """


class _Response(BaseModel):
    steps: list[StepRow]


@dataclass(frozen=True)
class ClassificationResult:
    """What one strategy's classification produced, including how it went.

    The bookkeeping fields are not diagnostics-for-diagnostics'-sake: `repairs` and
    `chunks` are the numerators of M1-9's DoD, and a parse-failure rate that cannot be
    computed from the object the pipeline already holds would have to be recomputed from
    logs at measurement time.
    """

    strategy: str
    item_id: str
    rows: tuple[StepRow, ...] = ()
    #: `{"reason": "classifier_parse_failure", "affects": [...]}` when both attempts on any
    #: chunk failed. C4.3 degrades the **strategy**, not the chunk: a trace annotated for
    #: steps 1-25 and blank for 26-50 invites the reader to treat the blank half as
    #: "nothing found there", which is the opposite of what happened.
    degraded: dict[str, Any] | None = None
    chunks: int = 0
    #: Chunks that needed the repair retry and then succeeded. A rising number here is the
    #: early warning that precedes a rising parse-failure rate.
    repairs: int = 0
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    #: Per-call HTTP latency, in order. The SUM is what the report shows; the individual
    #: numbers are what a latency investigation needs, and recomputing them from a log
    #: after the fact is exactly the thing this project keeps being unable to do.
    call_ms: tuple[int, ...] = ()
    truncated_rationales: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.degraded is None

    def by_step_id(self) -> dict[str, StepRow]:
        return {row.step_id: row for row in self.rows}


def chunk_steps(steps: list[Step], size: int | None = None) -> list[list[Step]]:
    """Split a trace's steps into runs of at most `size`, preserving order.

    The cap comes from config so the failure lever S3 names first -- reduce batch size --
    is turnable without a code change during a measurement run.
    """
    size = size if size is not None else int(os.environ.get("CLASSIFY_CHUNK_SIZE", "25"))
    if size < 1:
        raise ValueError(f"CLASSIFY_CHUNK_SIZE must be >= 1, got {size}")
    return [steps[i : i + size] for i in range(0, len(steps), size)]


def _render_steps(steps: list[Step], *, start: int) -> str:
    lines = []
    for offset, step in enumerate(steps):
        text = step.text.strip() or "(empty)"
        lines.append(f"[{start + offset + 1}] ({step.step_id}) <{step.kind}> {text}")
    return "\n".join(lines)


def render_prompt(
    trace: NormalizedTrace, chunk: list[Step], *, item_prompt: str, preceding: list[Step]
) -> str:
    """Render the committed prompt for one chunk.

    **The preceding steps travel with every chunk, and they have to.** The validity
    question is "is this step sound *given only the preceding steps*" -- a chunk sent
    without its history is being asked a question it cannot answer, and the model would
    have no way to say so. It would answer anyway, plausibly, which is the failure this
    project keeps finding in other forms.

    Input tokens are the cheap half of the trade. The expensive half -- output -- is what
    chunking protects, and it is unaffected by carrying context.
    """
    template = _PROMPT.read_text()
    # Strip the leading HTML comment: it is instructions to the maintainer about editing
    # this file, and sending a model a note about which CI job compares it to the rubric
    # is noise at best.
    if template.startswith("<!--"):
        template = template.split("-->", 1)[1].lstrip("\n")

    context_block = ""
    if preceding:
        context_block = (
            "PRECEDING STEPS (context only -- do NOT return rows for these):\n"
            + _render_steps(preceding, start=0)
            + "\n\n"
        )
    step_ids = "\n".join(step.step_id for step in chunk)
    replacements = {
        "{item_prompt}": item_prompt,
        "{context_block}": context_block,
        "{steps_block}": _render_steps(chunk, start=len(preceding)),
        "{final_answer}": trace.final_answer or "(no answer was given)",
        "{step_id_list}": step_ids,
        "{n_steps}": str(len(chunk)),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def _extract_json(text: str) -> Any:
    """Parse the response body, tolerating a markdown fence the prompt asked it not to use.

    Tolerated rather than rejected because a fence is a formatting habit, not a failed
    answer, and the rows inside it are real. What is NOT tolerated further down is a
    missing or extra `step_id` -- the difference is that one costs nothing to accept and
    the other costs the integrity of the label set.
    """
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        body = body.rsplit("```", 1)[0]
    return json.loads(body)


def _truncate_rationale(row: StepRow) -> tuple[StepRow, bool]:
    """Cap the rationale rather than failing the chunk over it.

    C4.3 caps it at 200 characters and the prompt says so. But the rationale is **display
    text**, not a measurement: nothing downstream computes on it. Failing a strategy's
    entire label set -- 25 real behavior and validity judgements -- because one sentence
    ran to 214 characters would destroy data to enforce a formatting rule. It is capped,
    the cap is counted, and the count is reported so a prompt that systematically
    overruns is visible rather than invisible.
    """
    if len(row.rationale) <= RATIONALE_MAX:
        return row, False
    return row.model_copy(update={"rationale": row.rationale[: RATIONALE_MAX - 1] + "…"}), True


def validate_rows(payload: Any, chunk: list[Step]) -> list[StepRow]:
    """Rows for exactly this chunk's steps, or a `ClassifierParseFailure` naming why.

    The id check is set equality, not a count: 25 rows that are the wrong 25 ids is the
    same failure as 24 rows, and a length check alone would let a duplicated id through
    while a real step went unlabelled.
    """
    try:
        parsed = _Response.model_validate(payload)
    except ValidationError as exc:
        raise ClassifierParseFailure(_first_errors(exc)) from exc

    wanted = [step.step_id for step in chunk]
    got = [row.step_id for row in parsed.steps]
    if len(set(got)) != len(got):
        dupes = sorted({sid for sid in got if got.count(sid) > 1})
        raise ClassifierParseFailure(f"duplicate step_id in the response: {dupes}")
    missing = [sid for sid in wanted if sid not in set(got)]
    extra = [sid for sid in got if sid not in set(wanted)]
    if missing or extra:
        raise ClassifierParseFailure(
            f"step_id mismatch: {len(got)} rows for {len(wanted)} steps. "
            f"Missing {missing[:5]}{'...' if len(missing) > 5 else ''}; "
            f"extra {extra[:5]}{'...' if len(extra) > 5 else ''}. "
            f"Return exactly one row per listed step_id, using the ids verbatim."
        )
    order = {sid: i for i, sid in enumerate(wanted)}
    return sorted(parsed.steps, key=lambda row: order[row.step_id])


def _first_errors(exc: ValidationError, limit: int = 4) -> str:
    """A repair message a model can act on: the field, the value, and the rule.

    Pydantic's full error dump for a 25-row response can run to kilobytes and would push
    the actual instruction out of the model's attention. The first few are enough --
    they are almost always the same mistake repeated.
    """
    parts = []
    for err in exc.errors()[:limit]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    more = len(exc.errors()) - len(parts)
    return "; ".join(parts) + (f" (and {more} more)" if more > 0 else "")


def classify(
    trace: NormalizedTrace,
    *,
    item_prompt: str,
    cassette_prefix: str | None = None,
) -> ClassificationResult:
    """Classify and triage one strategy's trace. The module's one entry point.

    Returns a `ClassificationResult` in both outcomes rather than raising on failure: a
    degraded arm still renders, and the report needs the `degraded` block to say so. An
    exception here would take the other two arms down with it (B6.5).
    """
    labelled = [step for step in trace.steps]
    if not labelled:
        # A Direct-arm trace with no reasoning and no answer. Zero steps is a real state
        # (C4.2's first named edge case), not a failure, and calling a model to classify
        # nothing would bill for a question with no content.
        return ClassificationResult(
            strategy=trace.strategy,
            item_id=trace.item_id,
            notes=("no steps to classify",),
        )

    chunks = chunk_steps(labelled)
    rows: list[StepRow] = []
    call_ms: list[int] = []
    calls = repairs = truncations = 0
    prompt_tokens = completion_tokens = reasoning_tokens = latency = 0
    seen = 0

    for index, chunk in enumerate(chunks):
        prompt = render_prompt(trace, chunk, item_prompt=item_prompt, preceding=labelled[:seen])
        cassette = f"{cassette_prefix}.c{index}" if cassette_prefix else None
        try:
            chunk_rows, result, used_repair = _classify_chunk(prompt, chunk, cassette=cassette)
        except ClassifierParseFailure as exc:
            return ClassificationResult(
                strategy=trace.strategy,
                item_id=trace.item_id,
                degraded={
                    "reason": "classifier_parse_failure",
                    "affects": ["behavior", "validity"],
                    "detail": f"chunk {index + 1}/{len(chunks)}: {exc}",
                },
                chunks=len(chunks),
                repairs=repairs + 1,
                calls=calls + 2,
                notes=("rendered unannotated -- labels are not fabricated (C4.3)",),
            )
        calls += 2 if used_repair else 1
        repairs += 1 if used_repair else 0
        capped = [_truncate_rationale(row) for row in chunk_rows]
        rows.extend(row for row, _ in capped)
        truncations += sum(1 for _, was in capped if was)
        prompt_tokens += result.prompt_tokens
        completion_tokens += result.completion_tokens
        reasoning_tokens += result.reasoning_tokens or 0
        latency += result.latency_ms
        call_ms.append(result.latency_ms)
        seen += len(chunk)

    return ClassificationResult(
        strategy=trace.strategy,
        item_id=trace.item_id,
        rows=tuple(rows),
        chunks=len(chunks),
        repairs=repairs,
        calls=calls,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        reasoning_tokens=reasoning_tokens,
        latency_ms=latency,
        call_ms=tuple(call_ms),
        truncated_rationales=truncations,
    )


def _classify_chunk(
    prompt: str, chunk: list[Step], *, cassette: str | None
) -> tuple[list[StepRow], AnalysisResult, bool]:
    """One chunk: the call, the validation, and the single repair retry.

    **Exactly one retry, and it is handed the validation error.** Retrying blind would be
    a coin flip at the price of a call; the error message is the only thing that makes the
    second attempt different from the first. A second failure is not retried again --
    C4.3 fixes the count at one, and an unbounded repair loop is how a parse-failure rate
    turns into a cost incident.
    """
    result = analyze(prompt, cassette=cassette)
    try:
        return validate_rows(_extract_json(result.text), chunk), result, False
    except (ClassifierParseFailure, json.JSONDecodeError) as first:
        repair_prompt = (
            f"{prompt}\n\n"
            f"YOUR PREVIOUS RESPONSE WAS REJECTED: {first}\n"
            f"Return only the JSON object described above, with exactly {len(chunk)} rows."
        )
        # The repair attempt gets its own cassette: it is a different request, and a
        # recorder that overwrote the first would make the replayed pipeline take a path
        # the live one did not.
        retry_cassette = f"{cassette}.repair" if cassette else None
        retried = analyze(repair_prompt, cassette=retry_cassette)
        try:
            return validate_rows(_extract_json(retried.text), chunk), retried, True
        except (ClassifierParseFailure, json.JSONDecodeError) as second:
            raise ClassifierParseFailure(f"after repair retry: {second}") from second
