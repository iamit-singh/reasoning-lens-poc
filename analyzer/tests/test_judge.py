"""The escalation tier — C4.4, M2-5.

**The selection policy is the part that has to be right**, and it is pure arithmetic over
rows, so most of this file needs no model at all. A policy that is only exercised through a
live call is a policy nobody re-checks before changing it.

The other half is about what the tier must not do: agree with the cheap pass by default,
merge two verdicts into a third nobody validated, or lose the triage verdicts when the
expensive call fails.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from rlens import judge as J
from rlens.contracts import Step, StepRow


def _step(i: int, text: str = "some reasoning") -> Step:
    return Step(step_id=f"thinking:s:{i}", ordinal=i, kind="thought", text=text, span_id="s")


def _row(i: int, **over: Any) -> StepRow:
    data = {
        "step_id": f"thinking:s:{i}",
        "behavior": "linear",
        "behavior_confidence": 0.9,
        "verdict": "sound",
        "validity_confidence": 0.95,
        "error_type": None,
        "rationale": "fine",
    }
    data.update(over)
    return StepRow(**data)


# ------------------------------------------------------------------ C4.4's three conditions
def test_an_unsound_step_always_escalates() -> None:
    assert J.should_escalate(
        _row(0, verdict="unsound", error_type="arithmetic", validity_confidence=0.99), _step(0)
    )


def test_a_confidently_unverifiable_step_does_NOT_escalate() -> None:
    """**This assertion is inverted from what it was, and the reason is a measurement.**

    It used to read `verdict != "sound"` is the condition, on the rationale that *"a
    confidently unverifiable step is exactly the kind a stronger model may be able to
    verify."* Over the corpus that clause selected 158 of 270 steps (58.5%, against t7's
    25% bar) and **157 of the 158 were `unverifiable`** -- the clause was reading
    *uncheckable* as *doubtful* on a corpus that is half unverifiable by design.

    The rationale does not survive reading `escalate.md`: it asks the **same question under
    the same constraint** ("judge each step GIVEN ONLY the steps that precede it") with the
    same definition of `unverifiable`. The stronger model gets the same text and the same
    absent citation. It is not better placed to verify it; it is asked not to try.
    """
    assert not J.should_escalate(
        _row(0, verdict="unverifiable", validity_confidence=0.99), _step(0)
    )


def test_an_unverifiable_step_the_judge_was_UNSURE_about_still_escalates() -> None:
    """The half of the old clause that survives, and the case where a second opinion adds
    something: the cheap model said "I cannot check this" and was not confident about even
    that."""
    assert J.should_escalate(_row(0, verdict="unverifiable", validity_confidence=0.60), _step(0))


def test_a_low_confidence_sound_step_escalates() -> None:
    assert J.should_escalate(_row(0, validity_confidence=0.69), _step(0))
    assert not J.should_escalate(_row(0, validity_confidence=0.71), _step(0))


def test_a_numeric_step_escalates_at_a_higher_confidence_bar() -> None:
    """Arithmetic is precisely where cheap judges fail (Part A §A6), so numeric steps get a
    stricter threshold than prose ones. 0.80 passes for prose and escalates for arithmetic."""
    numeric = _step(0, "So 17 x 4 = 68 and the total is 68.")
    prose = _step(0, "The remaining constraint is about ordering, not quantity.")
    assert J.should_escalate(_row(0, validity_confidence=0.80), numeric)
    assert not J.should_escalate(_row(0, validity_confidence=0.80), prose)


@pytest.mark.parametrize(
    "text",
    [
        "17 x 4 = 68",
        "3+4 = 7",
        "12/4=3",
        "increase of 15%",
        "raise by 20 percent",
        "5 \u00d7 6 = 30",
    ],
)
def test_numeric_detection_is_generous(text: str) -> None:
    """Over-selecting costs tokens; under-selecting costs recall on the class C4.4 singles
    out. That asymmetry is not close, so the regex errs wide."""
    assert J.is_numeric(text)


def test_prose_without_a_computation_is_not_numeric() -> None:
    assert not J.is_numeric("There are three rooms and the question asks about ordering.")


# ------------------------------------------------------------------ the cap
def test_the_cap_drops_the_least_doubtful_steps() -> None:
    """**Ordering is the whole reason the cap is defensible.** Dropping by list order would
    make which steps got a second opinion depend on where they appeared in the trace."""
    rows = [
        _row(0, validity_confidence=0.10),
        _row(1, verdict="unsound", error_type="logical", validity_confidence=0.90),
        _row(2, validity_confidence=0.50),
        _row(3, validity_confidence=0.65),
    ]
    steps = {s.step_id: s for s in (_step(0), _step(1), _step(2), _step(3))}
    selected, capped, rate = J.select(rows, steps, cap=2)

    assert capped is True
    assert rate == 1.0
    # unsound first, then ascending confidence -- so s:1 and s:0, never s:3.
    assert [r.step_id for r in selected] == ["thinking:s:1", "thinking:s:0"]


def test_the_cap_does_not_bind_when_few_steps_qualify() -> None:
    rows = [_row(0), _row(1), _row(2, validity_confidence=0.4)]
    steps = {s.step_id: s for s in (_step(0), _step(1), _step(2))}
    selected, capped, rate = J.select(rows, steps, cap=8)
    assert len(selected) == 1 and capped is False
    assert rate == pytest.approx(1 / 3)


def test_the_rate_is_reported_so_a_prompt_bug_is_visible() -> None:
    """C4.4: above 25% means the triage confidences are miscalibrated — *"treat it as a
    prompt bug, not a budget problem"*. Raising the cap in response would spend the C11
    latency budget to hide a prompt defect."""
    rows = [_row(i, validity_confidence=0.2) for i in range(10)]
    steps = {s.step_id: s for s in (_step(i) for i in range(10))}
    _, _, rate = J.select(rows, steps, cap=8)
    assert rate > J.PROMPT_BUG_RATE


# ------------------------------------------------------------------ the prompt
def test_the_prompt_does_not_reveal_the_first_pass_verdict() -> None:
    """**The failure this prompt is written against**: a stronger model, told the cheap one
    flagged a step, agrees with the flag. That is not a second opinion, it is an expensive
    echo — and it would make the tier look like it works while making the flagged set
    strictly larger."""
    rows = [_row(0, verdict="unsound", error_type="arithmetic"), _row(1)]
    ordered = [_step(0, "17 x 4 = 78"), _step(1, "so the total is 78")]
    steps = {s.step_id: s for s in ordered}
    selected, _, _ = J.select(rows, steps, cap=8)
    prompt = J.render_prompt(selected, steps, ordered, item_prompt="p")

    assert "unsound" in prompt  # it is an allowed ANSWER
    assert "arithmetic" in prompt  # ditto, as an error_type option
    # ...but the per-step verdict the cheap pass gave must not appear beside the step.
    assert "flagged the steps below" in prompt
    assert "You are not told what the cheaper model decided" in prompt


def test_the_prompt_prefers_sound_for_terse_steps() -> None:
    """Terseness is what the cheap pass most often mistakes for a defect."""
    prompt = J._PROMPT.read_text()
    assert "Prefer `sound` when the step is correct but terse" in prompt


def test_the_preceding_trace_travels_with_the_escalated_steps() -> None:
    """ "Sound given only the preceding steps" cannot be answered from a step in isolation —
    and sharing the context is why this is one batched call rather than N."""
    rows = [_row(0), _row(1), _row(2, validity_confidence=0.3)]
    ordered = [_step(0, "first"), _step(1, "second"), _step(2, "third")]
    steps = {s.step_id: s for s in ordered}
    selected, _, _ = J.select(rows, steps, cap=8)
    prompt = J.render_prompt(selected, steps, ordered, item_prompt="p")

    assert "THE TRACE SO FAR" in prompt
    assert "first" in prompt and "second" in prompt
    assert "do NOT return rows for these" in prompt


def test_the_rendered_prompt_substitutes_everything() -> None:
    rows = [_row(0, validity_confidence=0.2)]
    ordered = [_step(0)]
    steps = {s.step_id: s for s in ordered}
    prompt = J.render_prompt(rows, steps, ordered, item_prompt="What is 6x7?")
    for token in (
        "{item_prompt}",
        "{context_block}",
        "{steps_block}",
        "{step_id_list}",
        "{n_steps}",
    ):
        assert token not in prompt


# ------------------------------------------------------------------ applying the verdict
def test_the_escalated_verdict_replaces_rather_than_merges() -> None:
    """Two verdicts on one step, with a rule for combining them, is a third judge nobody
    validated and no number on the calibration page describes."""
    rows = [_row(0, verdict="unsound", error_type="arithmetic", validity_confidence=0.8), _row(1)]
    outcome = J.EscalationOutcome(
        rows={
            "thinking:s:0": J.EscalatedRow(
                step_id="thinking:s:0",
                verdict="sound",
                validity_confidence=0.93,
                error_type=None,
                rationale="the arithmetic is correct; the step is terse, not wrong",
            )
        }
    )
    merged = {r.step_id: r for r in J.apply(rows, outcome)}

    assert merged["thinking:s:0"].verdict == "sound"
    assert merged["thinking:s:0"].error_type is None
    assert merged["thinking:s:0"].validity_confidence == pytest.approx(0.93)
    # The behavior label is not the escalation tier's business (C4.4).
    assert merged["thinking:s:0"].behavior == "linear"
    # An un-escalated row is untouched.
    assert merged["thinking:s:1"].validity_confidence == pytest.approx(0.95)


def test_changed_verdicts_are_recorded_because_that_is_what_justifies_the_tier() -> None:
    """C4.4's DoD is a measured recall delta over triage-alone. If it comes back near zero,
    trigger t9 says publish it — escalation that did not earn its tokens is a finding and a
    Month-3 simplification, not an embarrassment."""
    rows = [_row(0, verdict="unsound", error_type="logical"), _row(1, validity_confidence=0.5)]
    ordered = [_step(0), _step(1)]

    def stub(prompt: str, **kwargs: Any) -> Any:
        from rlens.llm import AnalysisResult

        assert kwargs.get("tier") == "escalate", "the tier must select the stronger pin"
        body = {
            "steps": [
                {
                    "step_id": "thinking:s:0",
                    "verdict": "sound",
                    "validity_confidence": 0.9,
                    "error_type": None,
                    "rationale": "correct but terse",
                },
                {
                    "step_id": "thinking:s:1",
                    "verdict": "sound",
                    "validity_confidence": 0.88,
                    "error_type": None,
                    "rationale": "fine",
                },
            ]
        }
        return AnalysisResult(
            text=json.dumps(body),
            model="strong",
            finish_reason="stop",
            backend="hybrid",
            prompt_tokens=1,
            completion_tokens=1,
            reasoning_tokens=0,
            attempts=1,
            latency_ms=1,
        )

    import rlens.judge as mod

    original, mod.analyze = mod.analyze, stub
    try:
        outcome = J.escalate(rows, ordered, item_prompt="p")
    finally:
        mod.analyze = original

    assert set(outcome.changed) == {"thinking:s:0"}  # s:1 was already sound
    assert outcome.calls == 1


def test_a_failed_escalation_keeps_the_triage_verdicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """They are real judgements that cost a call, and the report renders them perfectly well
    with `escalated: false`. Losing them to a transport failure would be paying twice for
    nothing."""
    from rlens.llm import ProviderError

    def failing(*args: Any, **kwargs: Any) -> Any:
        raise ProviderError("deadline")

    monkeypatch.setattr(J, "analyze", failing)
    rows = [_row(0, verdict="unsound", error_type="logical")]
    outcome = J.escalate(rows, [_step(0)], item_prompt="p")

    assert outcome.rows == {}
    assert "triage verdicts kept" in outcome.note
    assert J.apply(rows, outcome)[0].verdict == "unsound"


def test_a_short_response_upgrades_what_came_back_and_keeps_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**Deliberately the opposite of C4.3's rule, and the difference is worth stating.**
    There, a missing row would have to be INVENTED to complete the set, so the whole batch
    fails. Here a missing row simply is not upgraded — the step keeps a real verdict a real
    judge produced."""
    from rlens.llm import AnalysisResult

    def partial(*args: Any, **kwargs: Any) -> AnalysisResult:
        body = {
            "steps": [
                {
                    "step_id": "thinking:s:0",
                    "verdict": "sound",
                    "validity_confidence": 0.9,
                    "error_type": None,
                    "rationale": "fine",
                }
            ]
        }
        return AnalysisResult(
            text=json.dumps(body),
            model="strong",
            finish_reason="stop",
            backend="hybrid",
            prompt_tokens=1,
            completion_tokens=1,
            reasoning_tokens=0,
            attempts=1,
            latency_ms=1,
        )

    monkeypatch.setattr(J, "analyze", partial)
    rows = [
        _row(0, verdict="unsound", error_type="logical"),
        _row(1, verdict="unsound", error_type="factual"),
    ]
    outcome = J.escalate(rows, [_step(0), _step(1)], item_prompt="p")
    merged = {r.step_id: r for r in J.apply(rows, outcome)}

    assert merged["thinking:s:0"].verdict == "sound"
    assert merged["thinking:s:1"].verdict == "unsound"
    assert "keep triage" in outcome.note


def test_nothing_to_escalate_costs_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("should not have called the stronger model")

    monkeypatch.setattr(J, "analyze", boom)
    outcome = J.escalate(
        [_row(0), _row(1)], [_step(0, "prose"), _step(1, "prose")], item_prompt="p"
    )
    assert outcome.rows == {} and outcome.calls == 0


# ------------------------------------------------------------------ the pin
def test_the_escalation_pin_must_differ_from_the_triage_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**The tier's entire claim is that a stronger model produced the verdict.** One id for
    both would keep the mechanism's name in the report while deleting the mechanism."""
    from rlens.versions import escalator_pin

    monkeypatch.setenv("MODEL_ANALYZE", "gpt-5-mini-2025-08-07")
    monkeypatch.setenv("MODEL_ESCALATE", "gpt-5-mini-2025-08-07")
    with pytest.raises(RuntimeError, match="are both"):
        escalator_pin()

    monkeypatch.setenv("MODEL_ESCALATE", "gpt-5-2025-08-07")
    assert escalator_pin() == "gpt-5-2025-08-07"


def test_an_aliased_escalation_pin_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from rlens.versions import escalator_pin

    monkeypatch.setenv("MODEL_ANALYZE", "gpt-5-mini-2025-08-07")
    monkeypatch.setenv("MODEL_ESCALATE", "gpt-5-chat-latest")
    with pytest.raises(RuntimeError, match="alias"):
        escalator_pin()


def test_an_unknown_tier_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from rlens.llm import ProviderError, analyze

    monkeypatch.setenv("ANALYZER_BACKEND", "hybrid")
    with pytest.raises(ProviderError, match="tier must be"):
        analyze("p", tier="frontier")
