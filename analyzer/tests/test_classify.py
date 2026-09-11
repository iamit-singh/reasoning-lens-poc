"""The classifier's contract — C4.3, M1-9.

**Almost every test here is about a failure path, and that is the point.** The happy path
of this module is one HTTP call and a `model_validate`; what M1-9 is actually buying is a
specific, disciplined set of behaviours when the model answers badly:

* a missing row **degrades the strategy** rather than being filled in,
* the repair retry happens **exactly once** and is **told what was wrong**,
* a truncated response is a **hard error**, not something to retry,
* and nothing, anywhere, invents a label.

The model is driven by a scripted stub rather than a cassette throughout. A cassette
records what a model did once; it cannot be made to drop row 17 of 25 on demand, and row
17 going missing is the exact event this module exists to handle. That is the same
argument `test_react_loop.py` makes for arm 3's runaway-turn tests, and it is the reason
those tests caught things a cassette replay did not.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from rlens import classify as C
from rlens.contracts import NormalizedTrace, Step
from rlens.llm import AnalysisResult


def _step(ordinal: int, text: str = "Some reasoning.", kind: str = "thought") -> Step:
    return Step(
        step_id=f"thinking:span1:{ordinal}",
        ordinal=ordinal,
        kind=kind,  # type: ignore[arg-type]
        text=text,
        span_id="span1",
    )


def _trace(n: int, *, answer: str = "42") -> NormalizedTrace:
    steps = [_step(i) for i in range(n)]
    return NormalizedTrace(
        strategy="thinking",
        item_id="mb-01",
        steps=steps,
        final_answer=answer,
        trace_quality="full",
        model_pin="test",
        source_text="Some reasoning.",
    )


def _row(step_id: str, **over: Any) -> dict[str, Any]:
    row = {
        "step_id": step_id,
        "behavior": "linear",
        "behavior_confidence": 0.8,
        "verdict": "sound",
        "validity_confidence": 0.9,
        "error_type": None,
        "rationale": "ok",
    }
    row.update(over)
    return row


def _result(payload: Any) -> AnalysisResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return AnalysisResult(
        text=text,
        model="test-model",
        finish_reason="stop",
        backend="hybrid",
        prompt_tokens=10,
        completion_tokens=20,
        reasoning_tokens=5,
        attempts=1,
        latency_ms=100,
    )


class ScriptedAnalyzer:
    """Returns a queued response per call and records every prompt it was given."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str, **kwargs: Any) -> AnalysisResult:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("the classifier made more calls than the script allows")
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _result(nxt)


@pytest.fixture
def scripted(monkeypatch: pytest.MonkeyPatch):
    def install(*responses: Any) -> ScriptedAnalyzer:
        stub = ScriptedAnalyzer(*responses)
        monkeypatch.setattr(C, "analyze", stub)
        return stub

    return install


# ------------------------------------------------------------------ chunking (S3)
def test_chunking_caps_rather_than_fixes_the_batch() -> None:
    """S3's central finding: 25 is a cap, not a batch size. Traces run 2 to 141 steps."""
    steps = [_step(i) for i in range(141)]
    chunks = C.chunk_steps(steps, 25)
    assert [len(c) for c in chunks] == [25, 25, 25, 25, 25, 16]
    # Order preserved and nothing lost: the rows are stitched back on step_id, and a
    # reordering here would produce a report whose steps are in the wrong sequence.
    assert [s.step_id for c in chunks for s in c] == [s.step_id for s in steps]


def test_a_short_trace_is_one_chunk() -> None:
    assert len(C.chunk_steps([_step(i) for i in range(6)], 25)) == 1


def test_chunk_size_must_be_positive() -> None:
    with pytest.raises(ValueError):
        C.chunk_steps([_step(0)], 0)


# ------------------------------------------------------------------ the prompt
def test_rendered_prompt_has_no_unsubstituted_placeholders() -> None:
    trace = _trace(3)
    prompt = C.render_prompt(trace, trace.steps, item_prompt="What is 6x7?", preceding=[])
    for token in (
        "{item_prompt}",
        "{steps_block}",
        "{step_id_list}",
        "{n_steps}",
        "{final_answer}",
    ):
        assert token not in prompt, f"{token} was never substituted"
    assert "{context_block}" not in prompt


def test_the_maintainer_comment_is_not_sent_to_the_model() -> None:
    """The leading HTML comment is instructions about editing the file, not the prompt."""
    trace = _trace(2)
    prompt = C.render_prompt(trace, trace.steps, item_prompt="p", preceding=[])
    assert "byte for byte" not in prompt
    assert prompt.startswith("You are analysing one reasoning trace")


def test_the_outcome_bias_guard_and_the_precedence_rule_are_both_present() -> None:
    """C6's guard and C4.3's precedence are the two lines the rubric must mirror."""
    trace = _trace(2)
    prompt = C.render_prompt(trace, trace.steps, item_prompt="p", preceding=[])
    assert "Do NOT consider whether the final answer is correct" in prompt
    assert "backtracking > verification > backward_chaining > subgoal_setting > linear" in prompt


def test_later_chunks_carry_the_preceding_steps_as_context() -> None:
    """ "Sound GIVEN ONLY the preceding steps" is unanswerable without them.

    A chunk sent bare would still be answered — plausibly, and on no evidence.
    """
    trace = _trace(30)
    chunks = C.chunk_steps(list(trace.steps), 25)
    later = C.render_prompt(trace, chunks[1], item_prompt="p", preceding=chunks[0])
    assert "PRECEDING STEPS" in later
    assert "thinking:span1:0" in later
    # ...and the context block must not invite rows for those steps.
    assert "do NOT return rows for these" in later
    first = C.render_prompt(trace, chunks[0], item_prompt="p", preceding=[])
    assert "PRECEDING STEPS" not in first


def test_the_step_id_list_is_exactly_the_chunk() -> None:
    trace = _trace(30)
    chunks = C.chunk_steps(list(trace.steps), 25)
    prompt = C.render_prompt(trace, chunks[1], item_prompt="p", preceding=chunks[0])
    tail = prompt.split("using these `step_id` values exactly as written:")[1]
    listed = [ln.strip() for ln in tail.splitlines() if ln.strip().startswith("thinking:")]
    assert listed == [s.step_id for s in chunks[1]]


# ------------------------------------------------------------------ validation (C4.3)
def test_a_missing_step_id_is_a_parse_failure() -> None:
    """**The rule this module exists to enforce.** 24 rows for 25 steps is a failure."""
    chunk = [_step(i) for i in range(3)]
    payload = {"steps": [_row(s.step_id) for s in chunk[:2]]}
    with pytest.raises(C.ClassifierParseFailure, match="step_id mismatch"):
        C.validate_rows(payload, chunk)


def test_an_extra_step_id_is_a_parse_failure() -> None:
    chunk = [_step(i) for i in range(2)]
    payload = {"steps": [_row(s.step_id) for s in chunk] + [_row("thinking:span1:99")]}
    with pytest.raises(C.ClassifierParseFailure, match="step_id mismatch"):
        C.validate_rows(payload, chunk)


def test_a_duplicated_step_id_is_caught_even_though_the_count_is_right() -> None:
    """A length check alone would pass this while a real step went unlabelled."""
    chunk = [_step(0), _step(1)]
    payload = {"steps": [_row("thinking:span1:0"), _row("thinking:span1:0")]}
    with pytest.raises(C.ClassifierParseFailure, match="duplicate"):
        C.validate_rows(payload, chunk)


def test_rows_are_returned_in_the_chunk_order_not_the_model_order() -> None:
    chunk = [_step(0), _step(1), _step(2)]
    shuffled = [_row("thinking:span1:2"), _row("thinking:span1:0"), _row("thinking:span1:1")]
    rows = C.validate_rows({"steps": shuffled}, chunk)
    assert [r.step_id for r in rows] == [s.step_id for s in chunk]


@pytest.mark.parametrize(
    "bad",
    [
        {"behavior": "reflection"},  # not in the taxonomy
        {"verdict": "probably_fine"},  # not in the three validity values
        {"behavior_confidence": 1.4},  # outside [0, 1]
        {"validity_confidence": -0.1},
        {"error_type": "typo"},  # not one of C3.3's five
    ],
)
def test_a_value_outside_the_taxonomy_is_rejected(bad: dict[str, Any]) -> None:
    """Every one of these would otherwise reach a metric or a UI legend as a new class."""
    chunk = [_step(0)]
    with pytest.raises(C.ClassifierParseFailure):
        C.validate_rows({"steps": [_row("thinking:span1:0", **bad)]}, chunk)


def test_unsound_without_an_error_type_is_rejected() -> None:
    chunk = [_step(0)]
    payload = {"steps": [_row("thinking:span1:0", verdict="unsound", error_type=None)]}
    with pytest.raises(C.ClassifierParseFailure, match="must name its defect"):
        C.validate_rows(payload, chunk)


def test_an_error_type_on_a_sound_step_is_rejected_rather_than_nulled() -> None:
    """Silently nulling it would hide a confused classifier behind clean-looking data."""
    chunk = [_step(0)]
    payload = {"steps": [_row("thinking:span1:0", verdict="sound", error_type="arithmetic")]}
    with pytest.raises(C.ClassifierParseFailure, match="must be null"):
        C.validate_rows(payload, chunk)


def test_unknown_extra_keys_do_not_fail_the_chunk() -> None:
    """A model that volunteers a `notes` field has still answered the question."""
    chunk = [_step(0)]
    rows = C.validate_rows({"steps": [_row("thinking:span1:0", notes="chatty")]}, chunk)
    assert len(rows) == 1


def test_a_markdown_fence_is_tolerated() -> None:
    """A fence is a formatting habit, not a failed answer — the rows inside it are real."""
    body = json.dumps({"steps": [_row("thinking:span1:0")]})
    assert C._extract_json(f"```json\n{body}\n```")["steps"][0]["step_id"] == "thinking:span1:0"


# ------------------------------------------------------------------ the repair retry
def test_the_repair_retry_happens_once_and_is_told_what_was_wrong(scripted) -> None:
    trace = _trace(2)
    good = {"steps": [_row(s.step_id) for s in trace.steps]}
    stub = scripted({"steps": [_row("thinking:span1:0")]}, good)  # first: a row short
    res = C.classify(trace, item_prompt="p")

    assert res.ok and len(res.rows) == 2
    assert res.repairs == 1 and res.calls == 2
    assert len(stub.prompts) == 2
    assert "YOUR PREVIOUS RESPONSE WAS REJECTED" in stub.prompts[1]
    # The specific defect, not a generic "try again" — that is the only thing making the
    # second attempt different from the first.
    assert "step_id mismatch" in stub.prompts[1]


def test_two_failures_degrade_the_strategy_and_label_nothing(scripted) -> None:
    """**The rule that matters most.** No fabricated rows, no partial annotation."""
    trace = _trace(3)
    short = {"steps": [_row("thinking:span1:0")]}
    scripted(short, short)
    res = C.classify(trace, item_prompt="p")

    assert not res.ok
    assert res.rows == ()
    assert res.degraded is not None
    assert res.degraded["reason"] == "classifier_parse_failure"
    assert res.degraded["affects"] == ["behavior", "validity"]
    assert "chunk 1/1" in res.degraded["detail"]


def test_a_failure_in_a_late_chunk_degrades_the_whole_strategy(scripted) -> None:
    """A trace annotated 1-25 and blank 26-30 reads as "nothing found there". It is not."""
    trace = _trace(30)
    chunks = C.chunk_steps(list(trace.steps), 25)
    first_ok = {"steps": [_row(s.step_id) for s in chunks[0]]}
    scripted(first_ok, {"steps": []}, {"steps": []})
    res = C.classify(trace, item_prompt="p")

    assert not res.ok and res.rows == ()
    assert "chunk 2/2" in res.degraded["detail"]  # type: ignore[index]


def test_unparseable_json_also_goes_through_the_repair_path(scripted) -> None:
    trace = _trace(1)
    good = {"steps": [_row("thinking:span1:0")]}
    stub = scripted("this is not json at all", good)
    res = C.classify(trace, item_prompt="p")
    assert res.ok and res.repairs == 1
    assert "REJECTED" in stub.prompts[1]


# ------------------------------------------------------------------ rationale & bookkeeping
def test_an_overlong_rationale_is_capped_not_rejected(scripted) -> None:
    """Display text. Failing 25 real judgements over a formatting rule destroys data."""
    trace = _trace(1)
    scripted({"steps": [_row("thinking:span1:0", rationale="x" * 400)]})
    res = C.classify(trace, item_prompt="p")

    assert res.ok
    assert len(res.rows[0].rationale) == C.RATIONALE_MAX
    # ...and the cap is *counted*, so a prompt that systematically overruns is visible.
    assert res.truncated_rationales == 1


def test_usage_is_summed_across_chunks(scripted) -> None:
    trace = _trace(30)
    chunks = C.chunk_steps(list(trace.steps), 25)
    scripted(*({"steps": [_row(s.step_id) for s in c]} for c in chunks))
    res = C.classify(trace, item_prompt="p")

    assert res.ok and len(res.rows) == 30
    assert res.chunks == 2 and res.calls == 2
    assert res.completion_tokens == 40  # 20 per stubbed call
    assert res.by_step_id()["thinking:span1:29"].behavior == "linear"


def test_an_empty_trace_costs_no_call(scripted) -> None:
    """Zero steps is a real state (C4.2's first edge case), not a failure to classify."""
    trace = NormalizedTrace(
        strategy="direct",
        item_id="mb-01",
        steps=[],
        final_answer="",
        trace_quality="partial",
        model_pin="test",
    )
    stub = scripted()  # any call at all raises
    res = C.classify(trace, item_prompt="p")
    assert res.ok and res.rows == () and res.calls == 0
    assert stub.prompts == []


def test_a_truncation_is_not_swallowed_as_a_parse_failure(scripted) -> None:
    """S3 consequence 1: `length` is a config fault. Retrying reproduces it exactly, and
    reporting it as `classifier_parse_failure` would name the wrong cause."""
    from rlens.llm import AnalysisTruncated

    trace = _trace(2)
    scripted(AnalysisTruncated("the 16000-token output cap bound"))
    with pytest.raises(AnalysisTruncated):
        C.classify(trace, item_prompt="p")


# ------------------------------------------------------------------ the taxonomy itself
def test_the_precedence_constant_matches_the_prompt_verbatim() -> None:
    """If these drift, kappa measures rubric drift rather than classifier quality."""
    text = C._PROMPT.read_text()
    assert " > ".join(C.PRECEDENCE) in text


def test_every_taxonomy_label_appears_in_the_prompt() -> None:
    text = C._PROMPT.read_text()
    for label in C.PRECEDENCE:
        assert label in text
