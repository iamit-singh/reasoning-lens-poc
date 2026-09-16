"""The consistency checker's two rules — C4.5, M2-8.

**Both rules are about not crying wolf**, and both protect a published number (B4 #5: false
positives at or below 5% on known-good traces). So they are tested without a model: the
rules are arithmetic over a parsed response, and a test that needed a model to exercise
them would be a test nobody runs before changing them.

The third thing asserted here is a word that must not appear. C4.5 says "faithful" does not
occur in this component, its output or its UI copy — consistency asks whether the written
steps support the answer, faithfulness asks whether they are the reasoning that produced it,
and conflating them would let this project claim the harder one on the easier one's
evidence.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from rlens import consistency as C
from rlens.contracts import NormalizedTrace, Step


def _trace(n: int = 4) -> NormalizedTrace:
    steps = [
        Step(step_id=f"thinking:s:{i}", ordinal=i, kind="thought", text=f"step {i}", span_id="s")
        for i in range(n)
    ]
    return NormalizedTrace(
        strategy="thinking",
        item_id="mb-01",
        steps=steps,
        final_answer="42",
        trace_quality="full",
        model_pin="test",
    )


def _payload(**over: Any) -> dict[str, Any]:
    row = {"verdict": "entails", "cited_step_ids": [], "rationale": "the steps support it"}
    row.update(over)
    return row


# ------------------------------------------------------------------ rule 1: only contradicts flags
def test_only_contradicts_raises_a_flag() -> None:
    """**The whole of C4.5's false-positive argument is this.**

    Sound traces are routinely underdetermined by their own written steps — models skip
    algebra they consider obvious. Flagging that class is the single most likely way to
    blow B4 #5 and make the instrument look broken on stage.
    """
    trace = _trace()
    entails = C.interpret(_payload(verdict="entails"), trace)
    under = C.interpret(_payload(verdict="underdetermined"), trace)
    contra = C.interpret(_payload(verdict="contradicts", cited_step_ids=["thinking:s:2"]), trace)

    assert entails.flagged is False
    assert under.flagged is False
    assert contra.flagged is True


def test_underdetermined_is_recorded_even_though_it_is_not_shown() -> None:
    """Recorded, not discarded: the share of traces that are underdetermined is itself a
    finding about how much reasoning these models leave unwritten."""
    result = C.interpret(
        _payload(verdict="underdetermined", rationale="skips the algebra"), _trace()
    )
    assert result.verdict == "underdetermined"
    assert result.rationale


# ------------------------------------------------------------------ rule 2: cite or be downgraded
def test_contradicts_without_a_citation_is_downgraded() -> None:
    """C4.5 names this as the lever to pull *if* FP exceeds 5%. It is applied from the
    start instead: an accusation with no evidence is the shape a hallucinating judge
    produces, and there is no version of this project that would want to ship one."""
    result = C.interpret(_payload(verdict="contradicts", cited_step_ids=[]), _trace())
    assert result.verdict == "underdetermined"
    assert result.flagged is False
    assert result.downgraded is True
    # And it says so, rather than quietly presenting a different verdict than the judge gave.
    assert "downgraded" in result.rationale


def test_a_citation_naming_a_step_that_does_not_exist_does_not_count() -> None:
    """The UI links these ids. An invented one would be a dead link beside an accusation,
    and a judge inventing step ids is not one whose citations belong next to real ones."""
    result = C.interpret(
        _payload(verdict="contradicts", cited_step_ids=["thinking:s:99"]), _trace()
    )
    assert result.verdict == "underdetermined"
    assert result.downgraded is True
    assert result.cited_step_ids == ()


def test_a_mixed_citation_keeps_only_the_real_ids() -> None:
    result = C.interpret(
        _payload(verdict="contradicts", cited_step_ids=["thinking:s:1", "nope:0:0"]), _trace()
    )
    assert result.verdict == "contradicts"
    assert result.cited_step_ids == ("thinking:s:1",)
    assert result.downgraded is False


def test_the_downgrade_is_counted_rather_than_silent() -> None:
    """A high downgrade rate is a prompt problem, and a prompt problem with a number
    attached is fixable. One without is folklore."""
    assert C.interpret(_payload(verdict="contradicts"), _trace()).downgraded is True
    assert (
        C.interpret(
            _payload(verdict="contradicts", cited_step_ids=["thinking:s:0"]), _trace()
        ).downgraded
        is False
    )


# ------------------------------------------------------------------ shape and failure
def test_an_unknown_verdict_is_rejected() -> None:
    """A fourth verdict would reach the report and the UI as a state nothing renders."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        C.interpret(_payload(verdict="probably_fine"), _trace())


def test_an_overlong_rationale_is_capped() -> None:
    result = C.interpret(_payload(rationale="x" * 500), _trace())
    assert len(result.rationale) == C.RATIONALE_MAX


def test_a_short_trace_is_not_sent_to_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Direct arm is often one step plus an answer. Asking a model whether an answer
    follows from itself bills for a question with no content."""
    called = {"n": 0}

    def boom(*args: Any, **kwargs: Any) -> Any:
        called["n"] += 1
        raise AssertionError("should not have called the model")

    monkeypatch.setattr(C, "analyze", boom)
    assert C.check(_trace(1), item_prompt="p") is None
    assert called["n"] == 0


def test_a_failed_call_returns_none_rather_than_a_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    """**None, and specifically not `underdetermined`.** `underdetermined` is a judgement
    that the steps do not settle the question; reporting it when no judge ran would put a
    conclusion in the report that nothing reached."""
    from rlens.llm import ProviderError

    def failing(*args: Any, **kwargs: Any) -> Any:
        raise ProviderError("deadline")

    monkeypatch.setattr(C, "analyze", failing)
    assert C.check(_trace(), item_prompt="p") is None


def test_malformed_json_returns_none_and_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """One call, no repair retry. C4.3's retry exists because a malformed batch of 25 rows
    is worth another attempt; a single three-field object is a prompt problem, and a second
    call buys a second chance at the same coin flip."""
    from rlens.llm import AnalysisResult

    calls = {"n": 0}

    def garbage(*args: Any, **kwargs: Any) -> AnalysisResult:
        calls["n"] += 1
        return AnalysisResult(
            text="not json",
            model="m",
            finish_reason="stop",
            backend="hybrid",
            prompt_tokens=1,
            completion_tokens=1,
            reasoning_tokens=0,
            attempts=1,
            latency_ms=1,
        )

    monkeypatch.setattr(C, "analyze", garbage)
    assert C.check(_trace(), item_prompt="p") is None
    assert calls["n"] == 1


# ------------------------------------------------------------------ the forbidden word
def test_the_word_faithful_appears_nowhere_in_this_component() -> None:
    """C4.5: *"The word 'faithful' does not appear in this component, its output, or its UI
    copy."* Checked rather than remembered, because the two questions are close enough that
    the wrong word is a natural thing to type."""
    # The module docstring and the prompt's HTML comment are allowed to say the word in
    # order to forbid it. Nothing that reaches a model or a reader is.
    module_body = pathlib.Path(C.__file__).read_text().split('"""', 2)[-1].lower()
    prompt_body = C._PROMPT.read_text().split("-->", 1)[-1].lower()

    assert "faithful" not in module_body, "'faithful' appears in consistency.py's code"
    assert "faithful" not in prompt_body, "'faithful' appears in the prompt sent to the model"


def test_the_prompt_puts_underdetermined_forward_as_a_real_answer() -> None:
    """A prompt that treats "I cannot tell" as failure pushes those traces into
    `contradicts`, which is exactly how the FP target gets blown."""
    prompt = C._PROMPT.read_text()
    assert "underdetermined" in prompt
    assert "MUST cite at least one step id" in prompt


def test_the_rendered_prompt_substitutes_everything() -> None:
    trace = _trace()
    rendered = C.render_prompt(trace, item_prompt="What is 6x7?")
    for token in ("{item_prompt}", "{steps_block}", "{final_answer}", "{n_steps}"):
        assert token not in rendered
    assert "thinking:s:0" in rendered
    assert rendered.startswith("Given ONLY the numbered steps")


def test_a_fenced_response_is_tolerated() -> None:
    body = json.dumps(_payload())
    assert C._extract_json(f"```json\n{body}\n```")["verdict"] == "entails"


# ------------------------------------------------------- M2-8: the pipeline call site
def test_the_pipeline_leaves_consistency_null_while_the_flag_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**"We did not ask" must never render as "it is fine".**

    The checker existed for a week with the pipeline hardcoding `"consistency": None`, so
    turning the flag on changed nothing. Now the call site is real, which makes the
    OFF path worth pinning too: with the flag off no model is called AND the field is
    null -- not `entails`, which is a verdict nothing reached.
    """
    from rlens import pipeline

    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("no model call may happen while CONSISTENCY_ENABLED is off")

    monkeypatch.delenv("CONSISTENCY_ENABLED", raising=False)
    monkeypatch.setattr(C, "analyze", boom)
    assert pipeline._consistency(_trace(), {"prompt": "p"}) is None


def test_the_pipeline_runs_the_check_once_the_flag_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The converse, so the test above cannot pass by the wiring being absent again."""
    from rlens import pipeline

    monkeypatch.setenv("CONSISTENCY_ENABLED", "1")
    monkeypatch.setattr(
        C,
        "analyze",
        lambda *a, **k: type(
            "R",
            (),
            {"text": json.dumps(_payload(verdict="contradicts", cited_step_ids=["thinking:s:1"]))},
        )(),
    )
    # **Through `build_arm`, not through the helper.** Asserting on `_consistency` alone
    # still passes when the arm builder is hardcoded back to `"consistency": None` -- which
    # is the exact state this task found the code in, so it is the state the test must fail
    # in. Verified by re-introducing that line and watching this fail.
    arm = pipeline.build_arm(_trace(), None, item={"id": "mb-01", "prompt": "p"})
    assert arm["consistency"] is not None
    assert arm["consistency"]["verdict"] == "contradicts"


def test_a_failed_consistency_call_does_not_take_the_arm_down_with_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The verdict is an addition to the report, not a precondition for it.

    An arm whose 25 steps classified perfectly should not be discarded because one extra
    call timed out -- the steps are the measurement, this is commentary on them.
    """
    from rlens import pipeline
    from rlens.llm import ProviderError

    monkeypatch.setenv("CONSISTENCY_ENABLED", "1")

    def failing(*a: Any, **k: Any) -> Any:
        raise ProviderError("upstream 503")

    monkeypatch.setattr(C, "analyze", failing)
    assert pipeline._consistency(_trace(), {"prompt": "p"}) is None


def test_the_pipeline_names_a_cassette_for_the_consistency_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**A tier called without a cassette name silently leaves the offline pipeline.**

    `check()` takes `cassette=None` by default, and the first wiring used the default. With
    no key, `make record-cassettes` records nothing for this tier; then under `MOCK_LLM=1`
    the call has nothing to replay, fails, and returns None. The report renders
    `consistency: null` offline and a real verdict online -- which is exactly the
    divergence M2-16 says the cassettes exist to prevent, in the month the Frontend builds
    against `MOCK_LLM=1`.

    Nothing failed. Nothing looked wrong. The only visible symptom was zero
    `consistency.*` files in a cassette store nobody counts.
    """
    from rlens import pipeline

    seen: dict[str, Any] = {}

    def capture(prompt: str, *, cassette: str | None = None, **k: Any) -> Any:
        seen["cassette"] = cassette
        return type("R", (), {"text": json.dumps(_payload())})()

    monkeypatch.setenv("CONSISTENCY_ENABLED", "1")
    monkeypatch.setattr(C, "analyze", capture)
    pipeline.build_arm(_trace(), None, item={"id": "mb-03", "prompt": "p"})

    assert seen.get("cassette"), "the consistency call must carry a cassette name"
    assert "mb-03" in seen["cassette"] and "thinking" in seen["cassette"], seen["cassette"]
