"""`NormalizedTrace`, `Step` and their parts — C3.2.

Owner: M1-0 skeleton · **implemented by M1-8**, which needed a type for its output.
C3.2 nominally belongs to M1-6/M1-10; M1-6 built the emission side and left this a
skeleton, so the segmenter inherited it. `ReasoningReport` (C3.3) is still M1-10's and is
deliberately **not** here — it is the object G1 freezes, and freezing it early would make
that gate a formality.

Why these are Pydantic models and not dataclasses
-------------------------------------------------
C3.3 says this object is *"the frontend's props, the download artifact, the cached blob,
and the golden-test subject"*. `NormalizedTrace` is one layer below that and travels the
same way. Validation at the boundary is the whole point: a `kind` outside the four allowed
values, or a `step_id` that does not match its own parts, must fail where it is constructed
rather than three stages later in a classifier prompt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

#: C3.2. `tool_call` and `observation` are produced only by the ReAct arm's structural
#: path; `answer` is produced exactly once per trace; everything else is a `thought`.
StepKind = Literal["thought", "tool_call", "observation", "answer"]

Strategy = Literal["direct", "thinking", "react"]

#: C3.1's rule. `provider_summarised` is a distinct state from `partial`: the former means
#: the provider gave us a summary instead of the raw chain (so the text is real but not
#: verbatim), the latter that something is missing. Collapsing them would put a summarised
#: chain in front of a reviewer with nothing marking it as second-hand.
TraceQuality = Literal["full", "partial", "provider_summarised"]


class Step(BaseModel):
    """One segmented step. **`step_id` is the join key for every label ever written.**

    C3.2 fixes the format as `"{strategy}:{span_id}:{ordinal}"`, and the ordinal comes from
    the segmenter. Hazard 1 in the Month-1 breakdown is exactly this: any change to the
    segmenter after labelling begins renumbers the ordinals and silently detaches every
    label from its text. That is why the id is validated against its own parts here rather
    than merely formatted — a mismatch is a bug that would otherwise surface as κ drifting
    for no visible reason.
    """

    step_id: str
    ordinal: int = Field(ge=0)
    kind: StepKind
    text: str
    span_id: str
    #: Offsets into the step's **source text** — the normalised reasoning text for a
    #: `thought`, the answer text for an `answer`, the tool payload for the ReAct kinds.
    #: Offsets are into the NORMALISED text, and `NormalizedTrace` carries that text, so a
    #: UI highlight has something to index into. Offsets into a string nobody kept would be
    #: decoration.
    char_range: tuple[int, int] | None = None
    tokens_out: int | None = None

    @model_validator(mode="after")
    def _id_matches_its_parts(self) -> Step:
        expected = f"{self.step_id.split(':')[0]}:{self.span_id}:{self.ordinal}"
        if self.step_id != expected:
            raise ValueError(
                f"step_id {self.step_id!r} does not match its own parts "
                f"(expected {expected!r}). C3.2 fixes the format as "
                f"'{{strategy}}:{{span_id}}:{{ordinal}}', and every label written in "
                f"Month 2 joins on it."
            )
        return self


class Usage(BaseModel):
    """Token usage. Reasoning tokens are counted locally, not reported (S1, G0 check 2)."""

    input_tokens: int = 0
    output_tokens: int = 0
    #: None when the encoding for this model is unknown. A guessed count is worse than
    #: none: it is plausible and wrong, and every cost figure downstream inherits it.
    reasoning_tokens: int | None = None
    answer_tokens: int | None = None
    tokenizer: str | None = None


class Timings(BaseModel):
    """What the run cost in wall-clock terms. Populated by the runner, not the analyzer."""

    latency_ms: int | None = None
    turns: int | None = None


class NormalizedTrace(BaseModel):
    """C3.2. One arm's trace, segmented, with everything the classifier needs and nothing
    it does not.

    The analyzer's **only** input is a span tree (I1), and this is what a span tree becomes.
    Nothing here records where the tree came from: a third-party tree simply arrives with
    no reasoning text and degrades to `trace_quality: "partial"` (ADR-002).
    """

    strategy: Strategy
    item_id: str
    steps: list[Step]
    final_answer: str
    usage: Usage = Usage()
    timings: Timings = Timings()
    trace_quality: TraceQuality
    model_pin: str

    #: The normalised reasoning text every `thought` step's `char_range` indexes into.
    #: Not in C3.2's sketch, and it has to be: offsets into a string nobody kept cannot be
    #: used to highlight anything, and the alternative -- re-deriving the text from the
    #: spans at render time -- would re-run normalisation in a second place and let the two
    #: drift.
    source_text: str = ""

    @model_validator(mode="after")
    def _steps_are_ordered_and_answerable(self) -> NormalizedTrace:
        ordinals = [s.ordinal for s in self.steps]
        if ordinals != list(range(len(ordinals))):
            raise ValueError(
                f"step ordinals must be dense and ascending from 0, got {ordinals}. "
                f"A gap means a step was dropped after numbering, and `step_id` embeds "
                f"the ordinal."
            )
        if len({s.step_id for s in self.steps}) != len(self.steps):
            raise ValueError("duplicate step_id: the label join key must be unique")
        answers = [s for s in self.steps if s.kind == "answer"]
        if len(answers) > 1:
            raise ValueError(
                f"{len(answers)} answer steps. C4.2 makes the final answer a single "
                f"`answer` step, never more -- the UI and the consistency check both "
                f"assume one."
            )
        if answers and answers[-1] is not self.steps[-1]:
            raise ValueError("the answer step must be last")
        return self


# ---------------------------------------------------------------- the label vocabulary
# **These live here rather than in `classify.py` because two modules speak them.** The
# classifier produces these rows and the escalation tier (C4.4) re-judges them, and the
# layer contract puts those two in the SAME layer -- siblings, forbidden from importing
# each other. import-linter caught the shortcut the moment `judge.py` reached for
# `classify.StepRow`, which is exactly the kind of quiet coupling C2.2 exists to prevent.
#
# It is also the more honest home: these are the vocabulary of C3.3's output contract, not
# an implementation detail of whichever module happens to emit them first.

#: C4.3's taxonomy. Single-label with a stated precedence, because multi-label would make
#: Cohen's kappa inapplicable -- and the precedence rule is what makes single-labelling
#: reproducible between two annotators who never speak to each other.
Behavior = Literal["verification", "backtracking", "subgoal_setting", "backward_chaining", "linear"]

Verdict = Literal["sound", "unsound", "unverifiable"]

ErrorType = Literal["arithmetic", "logical", "factual", "constraint_violation", "unsupported_leap"]

#: C4.3's precedence, highest first. Not used to *pick* a label -- the model does that --
#: but it is the rubric's rule and the rubric and the prompt must not drift, so the one
#: machine-readable copy lives next to the prompt that states it.
PRECEDENCE: tuple[Behavior, ...] = (
    "backtracking",
    "verification",
    "backward_chaining",
    "subgoal_setting",
    "linear",
)

#: Display text, capped rather than validated -- see `_truncate_rationale`.
RATIONALE_MAX = 200


class StepRow(BaseModel):
    """One returned row, validated at the boundary.

    Strict about everything that becomes a measurement and forgiving about nothing else.
    `extra` keys are ignored rather than rejected: a model that adds a `notes` field has
    not failed to answer the question, and rejecting the whole chunk over it would trade
    25 real rows for a tidiness rule.
    """

    step_id: str
    behavior: Behavior
    behavior_confidence: float = Field(ge=0.0, le=1.0)
    verdict: Verdict
    validity_confidence: float = Field(ge=0.0, le=1.0)
    error_type: ErrorType | None = None
    rationale: str = ""

    @model_validator(mode="after")
    def _error_type_agrees_with_verdict(self) -> StepRow:
        """`error_type` names the defect in an `unsound` step, and means nothing otherwise.

        Checked rather than silently normalised. A row saying `sound` with
        `error_type: "arithmetic"` is a model that has not answered coherently, and the
        repair retry -- which is handed this exact message -- is the cheap place to find
        out whether it can. Quietly nulling the field would hide a confused classifier
        behind clean-looking data, and C4.6's flagged-step count reads these.
        """
        if self.verdict == "unsound" and self.error_type is None:
            raise ValueError(
                f"step {self.step_id}: verdict is 'unsound' but error_type is null. "
                f"An unsound step must name its defect."
            )
        if self.verdict != "unsound" and self.error_type is not None:
            raise ValueError(
                f"step {self.step_id}: verdict is {self.verdict!r} but error_type is "
                f"{self.error_type!r}. error_type must be null unless the verdict is 'unsound'."
            )
        return self
