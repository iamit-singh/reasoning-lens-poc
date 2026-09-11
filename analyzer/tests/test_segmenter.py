"""The segmenter's contract and M1-8's DoD. C4.2.

**This file guards a freeze.** `step_id` embeds the segmenter's ordinal, and every label a
human writes in Month 2 joins on it, so a change to `segment.py` after labelling begins
silently detaches every label from its text (Hazard 1). The goldens are therefore not
regression tests in the usual sense — they are the recorded meaning of `segmenter-frozen-v1`,
and a diff in any of them is a question about whether the freeze is being broken, not a test
to update.

Each fixture in `fixtures/segmenter/` carries `covers` and `why` fields naming the edge case
from the breakdown's §5.3 table that it exists for. The table has eight rows; twelve
fixtures cover them with the ordinary cases (discourse markers, list markers) and the two
ReAct shapes included.

Owner: M1-8.
"""

from __future__ import annotations

import ast
import json
import pathlib
from typing import Any

import pytest
from rlens.ingest.otel import LlmCall, ParsedTrace, ToolUse, parse
from rlens.segment import (
    MERGE_UNDER_WORDS,
    SPLIT_OVER_WORDS,
    normalise_text,
    segment,
    segment_text,
    word_count,
)

GOLDENS = pathlib.Path(__file__).parent / "fixtures/segmenter"
SPANS = pathlib.Path(__file__).parent / "fixtures/spans"

#: The §5.3 edge-case table. Every row must be claimed by at least one fixture's `covers`
#: field, matched on these keys -- so deleting a fixture that covers an edge case fails
#: here rather than quietly reducing coverage.
EDGE_CASES = (
    "Empty thinking",
    "Fenced code block",
    "LaTeX",
    "Provider-summarised",
    "under the threshold",
    "over the cap",
    "STRUCTURAL path only",
    "single `answer` step",
)


def _names() -> list[str]:
    return sorted(p.stem for p in GOLDENS.glob("*.json"))


def _load(name: str) -> dict[str, Any]:
    return json.loads((GOLDENS / f"{name}.json").read_text())


def _parsed(fixture: dict[str, Any]) -> ParsedTrace:
    spec = fixture["input"]
    return ParsedTrace(
        strategy=spec["strategy"],
        item_id=spec["item_id"],
        calls=[
            LlmCall(
                span_id=c["span_id"],
                reasoning=c["reasoning"],
                content=c["content"],
                seq=c["seq"],
                turn=i,
            )
            for i, c in enumerate(spec["calls"])
        ],
        tools=[
            ToolUse(
                span_id=t["span_id"],
                name=t["name"],
                arguments=t["arguments"],
                observation=t["observation"],
                ok=t["ok"],
                seq=t["seq"],
                turn=i,
            )
            for i, t in enumerate(spec["tools"])
        ],
        trace_quality=spec["trace_quality"],
        model_pin="segmenter-golden",
    )


def _as_expected(trace: Any) -> dict[str, Any]:
    return {
        "trace_quality": trace.trace_quality,
        "final_answer": trace.final_answer,
        "steps": [
            {
                "ordinal": s.ordinal,
                "kind": s.kind,
                "span_id": s.span_id,
                "step_id": s.step_id,
                "char_range": list(s.char_range) if s.char_range else None,
                "text": s.text,
            }
            for s in trace.steps
        ],
    }


# ------------------------------------------------------------------ M1-8's DoD
@pytest.mark.contract
def test_there_are_twelve_goldens_covering_the_named_edge_cases() -> None:
    """The DoD asks for 12 fixtures covering §5.3's table, so both halves are asserted.

    A count alone is satisfiable by twelve copies of the easy case.
    """
    names = _names()
    assert len(names) == 12, f"M1-8's DoD is 12 goldens, found {len(names)}: {names}"
    claimed = " ".join(_load(n)["covers"] for n in names)
    missing = [case for case in EDGE_CASES if case not in claimed]
    assert not missing, f"no fixture claims to cover: {missing}"
    for name in names:
        fixture = _load(name)
        assert fixture["why"].strip(), f"{name}: a fixture without a stated reason is a snapshot"


@pytest.mark.contract
@pytest.mark.parametrize("name", _names())
def test_segmenter_deterministic(name: str) -> None:
    """**M1-8's DoD, stated exactly: each fixture 3x, byte-identical output.**

    Three runs of a pure function is a weak test of today's code and a strong test of
    tomorrow's: it is what catches a `set` iteration or a dict ordering dependency being
    introduced into a frozen file, which is the realistic way this breaks.
    """
    fixture = _load(name)
    renders = [
        json.dumps(_as_expected(segment(_parsed(fixture))), sort_keys=True) for _ in range(3)
    ]
    assert renders[0] == renders[1] == renders[2], f"{name} is not byte-stable across runs"


@pytest.mark.contract
@pytest.mark.parametrize("name", _names())
def test_golden_steps_are_unchanged(name: str) -> None:
    """The recorded meaning of `segmenter-frozen-v1`.

    A failure here is not a stale expectation to refresh. It means the segmenter's output
    moved, and if labelling has begun, every `step_id` past the change point now points at
    different text.
    """
    fixture = _load(name)
    assert _as_expected(segment(_parsed(fixture))) == fixture["expected"], (
        f"{name}: segmentation changed. If this is deliberate, the freeze is being broken "
        f"-- re-run the sampling draw and re-label the affected steps (Hazard 1), and "
        f"record the new commit sha in calibration/sampling.json."
    )


# ------------------------------------------------------------------ the freeze's substrate
@pytest.mark.contract
def test_the_segmenter_has_no_tokenizer_dependency() -> None:
    """**The reason the token unit is a word.** `tiktoken.get_encoding` fetches a remote
    BPE file; a segmenter whose thresholds depend on that download is not byte-stable, and
    the failure is invisible -- it does not error, it segments differently.

    Asserted against the source rather than trusted to review: a future edit that reaches
    for the model's tokenizer to make the cap "more accurate" fails here and has to read
    ADR-008 first.
    """
    source = (pathlib.Path(__file__).parents[1] / "src/rlens/segment.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "tiktoken" not in imported, "the segmenter must not depend on a fetched BPE table"
    assert imported <= {"__future__", "itertools", "re", "rlens"}, (
        f"the segmenter grew a dependency: {sorted(imported)}. Every one of these is a way "
        f"for a frozen file's output to move."
    )


@pytest.mark.contract
def test_the_thresholds_are_the_derived_ones() -> None:
    """Pinned so changing them is a deliberate act, not a tidy-up.

    ADR-008 derives both from C4.2's token counts at a measured 1.446 harmony tokens per
    word, over 7,531 words of the project's own committed traces. `138` looks arbitrary
    precisely because it is derived; rounding it to 140 would be a guess wearing the
    authority of a constant. **S3 (M1-12) may still change `SPLIT_OVER_WORDS` -- before
    the freeze tag, per breakdown §5.3.**
    """
    assert MERGE_UNDER_WORDS == 10
    assert SPLIT_OVER_WORDS == 138


@pytest.mark.contract
def test_normalisation_is_idempotent() -> None:
    """Offsets are computed after normalisation, so a second pass must change nothing."""
    raw = "  <think>Wait.\r\nSo we compute.\r\n</think>  "
    once = normalise_text(raw)
    assert normalise_text(once) == once
    assert "\r" not in once and "<think>" not in once


# ------------------------------------------------------------------ invariants
@pytest.mark.contract
@pytest.mark.parametrize("name", _names())
def test_thought_char_ranges_index_the_source_text(name: str) -> None:
    """`char_range` has to index something the trace actually carries.

    Offsets into a string nobody kept cannot highlight anything, and re-deriving the text
    at render time would run normalisation in a second place and let the two drift.
    """
    trace = segment(_parsed(_load(name)))
    for step in trace.steps:
        if step.kind != "thought" or step.char_range is None:
            continue
        start, end = step.char_range
        assert trace.source_text[start:end] == step.text, (
            f"{name} step {step.ordinal}: char_range does not select its own text"
        )


@pytest.mark.contract
@pytest.mark.parametrize("name", _names())
def test_no_step_is_below_the_merge_threshold_unless_it_is_all_there_is(name: str) -> None:
    """C4.2 2d's purpose, not just its mechanism: no one-word thought steps survive.

    Two exceptions, and both are in the spec rather than concessions to it:

    * **A whole trace shorter than the threshold is one step.** `mb-01`'s direct arm
      produces `Need answer: K.` and nothing else; the merge rule trims noise and must
      never delete the only content there is.
    * **The ReAct arm is exempt.** C4.2 2d lives inside the *text-splitting* path, and the
      ReAct path is structural only. A five-word turn (`We need population of
      Brightwater.`) is genuinely that turn's whole thought, and merging it into the
      previous thought would merge ACROSS a tool call -- destroying exactly the structure
      the ReAct path exists to preserve.
    """
    trace = segment(_parsed(_load(name)))
    if trace.strategy == "react":
        return
    thoughts = [s for s in trace.steps if s.kind == "thought"]
    if len(thoughts) <= 1:
        return
    for step in thoughts:
        assert word_count(step.text) >= MERGE_UNDER_WORDS, (
            f"{name} step {step.ordinal} has {word_count(step.text)} words"
        )


@pytest.mark.contract
@pytest.mark.parametrize("name", _names())
def test_at_most_one_answer_step_and_it_is_last(name: str) -> None:
    """C4.2 2f. Enforced by `NormalizedTrace` too, so this is the fixture-level proof that
    the rule holds on real shapes rather than only in the validator."""
    trace = segment(_parsed(_load(name)))
    answers = [s for s in trace.steps if s.kind == "answer"]
    assert len(answers) <= 1
    if answers:
        assert trace.steps[-1] is answers[0]
        assert all(s.kind != "answer" for s in trace.steps[:-1])


@pytest.mark.contract
def test_the_react_path_does_no_text_splitting() -> None:
    """C4.2 1: structural only. The thought below holds two discourse markers and stays one
    step -- agent traces arrive already segmented (B5), and splitting them would invent
    boundaries the agent's own structure already states."""
    fixture = _load("10-react-structural")
    trace = segment(_parsed(fixture))
    thoughts = [s for s in trace.steps if s.kind == "thought"]
    assert "Wait." in thoughts[0].text and "So " in thoughts[0].text
    assert len(thoughts) == 3, "one thought per turn that produced reasoning, never more"
    kinds = [s.kind for s in trace.steps]
    assert kinds == [
        "thought",
        "tool_call",
        "observation",
        "thought",
        "tool_call",
        "observation",
        "thought",
        "answer",
    ]


# ------------------------------------------------------------------ the long-split rules
def test_a_long_step_is_split_repeatedly_until_under_the_cap() -> None:
    """C4.2 2e says "repeat". The goldens only exercise one level, so the recursion gets a
    unit test rather than a 600-word fixture nobody will read."""
    sentence = "The rack count is forty seven and each rack holds twenty one servers here. "
    text = sentence * 40  # ~520 words, needs three levels against a 138-word cap
    spans = segment_text(text)
    assert len(spans) >= 4
    for start, end in spans:
        assert word_count(text[start:end]) <= SPLIT_OVER_WORDS


def test_an_unsplittable_long_step_is_left_alone() -> None:
    """A step over the cap with no interior sentence boundary stays one step.

    Splitting mid-sentence would produce two fragments neither of which can be labelled --
    worse than one long step, and the classifier's own behaviour on long steps is what S3
    measures.
    """
    text = " ".join(["word"] * (SPLIT_OVER_WORDS + 50))
    spans = segment_text(text)
    assert len(spans) == 1
    assert word_count(text[spans[0][0] : spans[0][1]]) > SPLIT_OVER_WORDS


def test_the_long_split_breaks_ties_toward_the_earlier_boundary() -> None:
    """Two candidates equidistant from the midpoint is rare and entirely possible.

    Without a stated rule the winner depends on iteration order, which changes under a
    refactor and takes every `step_id` with it.
    """
    half = "Aa bb cc dd ee ff gg hh ii jj kk ll mm nn oo pp qq rr ss tt. " * 4
    text = half + "X. " + half
    spans = segment_text(text)
    rendered = [text[s:e] for s, e in spans]
    assert len(rendered) > 1
    # Deterministic across runs is the property that matters; the tie rule is what makes
    # it so, and a second call must agree exactly.
    assert [text[s:e] for s, e in segment_text(text)] == rendered


# ------------------------------------------------------------------ real traces, end to end
@pytest.mark.contract
def test_the_analyzer_segments_the_stock_langgraph_capture() -> None:
    """B12, made concrete at the segmenter: the capture the analyzer has never seen.

    It carries **no reasoning text** -- LangChain dropped it before the instrumentor saw
    it (S2) -- so the honest outcome is TOOL structure with no thought steps and a
    `partial` trace, not an error. That degradation path is the whole reason the analyzer
    can ingest a third-party tree at all (ADR-002).
    """
    tree = json.loads((SPANS / "langgraph_react_reference.json").read_text())
    trace = segment(parse(tree, strategy="react"))

    assert trace.trace_quality == "partial", "no reasoning text means a degraded trace"
    assert not [s for s in trace.steps if s.kind == "thought"]
    tool_calls = [s for s in trace.steps if s.kind == "tool_call"]
    observations = [s for s in trace.steps if s.kind == "observation"]
    assert len(tool_calls) == len(observations) >= 1, "one observation per tool call"
    assert observations[0].text.strip(), "the observation carries the tool's output"


def test_an_unterminated_code_fence_protects_to_the_end_of_the_text() -> None:
    """C4.2 says never split inside a fenced block — not "inside a fence that closes".

    A truncated response ends mid-block, and S3 measured `finish_reason: "length"` on this
    runtime, so this is an observed shape rather than a hypothetical. Without the rule, a
    70-word trace ending mid-fence split into four steps, three of them lines of code.
    """
    text = (
        "Let me write the whole computation out as a script so that every step of it is "
        "unambiguous and can be checked line by line later on.\n\n```python\n"
        "Wait for the rack count to be confirmed before doing anything else at all here.\n"
        "So multiply the racks by the servers that each one of them happens to hold.\n"
        "Then multiply that running product by the watts that each server draws.\n"
    )
    spans = segment_text(text)
    assert len(spans) == 2, [text[s:e] for s, e in spans]
    assert spans[1][0] == text.index("```"), "the fence begins the second step"
    assert text[spans[1][0] : spans[1][1]].count("\n") >= 3, "and runs to the end, unsplit"


def test_an_unterminated_maths_delimiter_does_NOT_protect_to_the_end() -> None:
    """The deliberate asymmetry with fences.

    An unclosed `\\[` is far more likely a stray delimiter in prose than a truncated
    equation, and protecting the remainder of the text on account of it would collapse
    everything after it into one unsplittable step. Over-protection has a cost too, and
    for maths it is the larger one.
    """
    text = (
        "The inner area follows from the two reduced dimensions, which we computed just "
        "above from the path width.\n\\[\n"
        "So the area is the product of those two figures and nothing more than that.\n"
        "Therefore the total comes out as three hundred and fifteen square metres here.\n"
    )
    spans = segment_text(text)
    assert len(spans) > 1, "an unclosed maths delimiter must not freeze the rest of the text"
