"""The span contract for arms 1-2. M1-6's DoD.

Runs the real runner under `MOCK_LLM=1` against committed cassettes, so the emission
path itself is exercised -- a test that asserted on a hand-written span tree would pass
forever while the emitter drifted away from it.

What is asserted here is the *contract*, not the content: which attributes must exist,
in which namespace, and what each arm's regime must look like. The numbers that vary
run-to-run (token counts, answers) are checked for shape and relationship, never for
exact value.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
from rlens.runner.arms import ARMS
from rlens.runner.run import (
    REGIME_SEPARATION_MAX_RATIO,
    ArmResult,
    check_regime_separation,
    run_arm,
)
from rlens.versions import GenerationPin

ITEM = "probe-01"

#: Harmony wraps each channel (`<|channel|>analysis<|message|>` and friends) in tokens
#: the runtime bills and the extracted text does not contain. Measured at exactly +10 for
#: both arms. 32 leaves room for a third channel without admitting a mis-tokenised text.
MAX_STRUCTURAL_RESIDUAL = 32

#: The pin the cassettes were recorded against. Stated here rather than read from the
#: environment so the test is hermetic -- CI has no `.env` and must not need one.
TEST_PIN = GenerationPin(
    model="gpt-oss:20b",
    digest="sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb",
    quantization="MXFP4",
    runtime="ollama 0.33.3",
    temperature=0.0,
    top_p=1.0,
    seed=20260910,
    reasoning_effort="medium",
)


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_LLM", "1")


def _run(strategy: str) -> ArmResult:
    return asyncio.run(run_arm(ARMS[strategy], ITEM, "unused under replay", pin=TEST_PIN))


@pytest.fixture(scope="module")
def results() -> dict[str, ArmResult]:
    os.environ["MOCK_LLM"] = "1"
    return {s: _run(s) for s in ("direct", "thinking")}


def _span(result: ArmResult, kind: str) -> dict[str, Any]:
    return next(s for s in result.spans if s["attributes"]["openinference.span.kind"] == kind)


# ------------------------------------------------------------------ tree shape (C4.1)
@pytest.mark.contract
@pytest.mark.parametrize("strategy", ["direct", "thinking"])
def test_one_root_chain_span_per_arm_with_an_llm_child(
    results: dict[str, ArmResult], strategy: str
) -> None:
    r = results[strategy]
    assert r.ok, r.failed_reason
    roots = [s for s in r.spans if s["parentSpanId"] is None]
    assert len(roots) == 1
    assert roots[0]["attributes"]["openinference.span.kind"] == "CHAIN"
    children = [s for s in r.spans if s["parentSpanId"] == roots[0]["spanId"]]
    assert [c["attributes"]["openinference.span.kind"] for c in children] == ["LLM"]


# ------------------------------------------------------------------ namespace (ADR-002)
@pytest.mark.contract
@pytest.mark.parametrize("strategy", ["direct", "thinking"])
def test_emits_the_openinference_namespace_and_no_gen_ai_keys(
    results: dict[str, ArmResult], strategy: str
) -> None:
    """ADR-002 §1. S2 measured that no real instrumentation emits `gen_ai.*`.

    Emitting names that nothing else emits would put the divergence back on our side --
    the analyzer would then need a branch for our trees and a branch for everyone
    else's, which is precisely the split ADR-002 exists to avoid.
    """
    attrs = _span(results[strategy], "LLM")["attributes"]
    assert not [k for k in attrs if k.startswith("gen_ai.")]
    for required in (
        "llm.model_name",
        "llm.input_messages.0.message.role",
        "llm.input_messages.0.message.content",
        "llm.output_messages.0.message.role",
        "llm.output_messages.0.message.content",
        "llm.token_count.prompt",
        "llm.token_count.completion",
        "llm.token_count.total",
    ):
        assert required in attrs, required


@pytest.mark.contract
def test_the_runner_emits_reasoning_text_that_langchain_drops(
    results: dict[str, ArmResult],
) -> None:
    """ADR-002 §2 -- the whole reason the emission layer exists.

    S2's control proved the runtime returns the trace and `ChatOpenAI` discards it. If
    this attribute stops being emitted, the analyzer has no reasoning to segment for
    arms 1-2 and the product has no subject.
    """
    attrs = _span(results["thinking"], "LLM")["attributes"]
    text = attrs.get("llm.output_messages.0.message.reasoning")
    assert isinstance(text, str) and text.strip(), "the thinking arm emitted no reasoning"
    assert "llm.output_messages.0.message.content" in attrs
    assert text != attrs["llm.output_messages.0.message.content"], (
        "reasoning and answer are the same string -- the split did not happen"
    )


@pytest.mark.contract
def test_our_own_attributes_stay_in_our_own_namespace(results: dict[str, ArmResult]) -> None:
    """`rlens.*` for what we compute, `llm.*`/`openinference.*` for what a standard
    instrumentation would emit. Blending them makes our trees quietly non-comparable
    with the third-party fixture, which is what the B12 evidence rests on."""
    attrs = _span(results["thinking"], "LLM")["attributes"]
    for ours in ("rlens.token_count.reasoning", "rlens.tokenizer", "rlens.budget_bound"):
        assert ours in attrs, ours
    # The locally-counted reasoning split must never masquerade as a standard attribute.
    assert "llm.token_count.reasoning" not in attrs


# ------------------------------------------------------------------ the pin (ADR-001)
@pytest.mark.contract
@pytest.mark.parametrize("strategy", ["direct", "thinking"])
def test_the_root_span_carries_the_pin_tuple_not_just_an_id(
    results: dict[str, ArmResult], strategy: str
) -> None:
    """ADR-001: an id does not reproduce a number, so the whole tuple travels."""
    attrs = _span(results[strategy], "CHAIN")["attributes"]
    for field in ("model", "digest", "quantization", "runtime", "temperature", "top_p", "seed"):
        assert f"rlens.pin.{field}" in attrs, field
    assert attrs["rlens.pin.fingerprint"] == TEST_PIN.fingerprint()
    assert attrs["rlens.strategy"] == strategy
    assert attrs["rlens.trace_quality"] in ("full", "partial", "provider_summarised")


# ------------------------------------------------------------------ the regimes (ADR-004)
@pytest.mark.contract
def test_the_two_arms_ran_in_different_regimes(results: dict[str, ArmResult]) -> None:
    """ADR-004. Arm 1 is a MINIMAL-reasoning baseline, and it has to actually be one.

    S7 found `reasoning_effort: "none"` and `think: false` are silently ignored by this
    model, so the request is not evidence -- the output is. Without this assertion the
    two arms could collapse into the same regime and every cost-of-thought number
    downstream would be wrong with nothing visibly broken.
    """
    d = results["direct"].completion
    t = results["thinking"].completion
    assert d is not None and t is not None
    assert d.requested_effort == "low"
    assert t.requested_effort == "medium"
    assert d.reasoning_tokens is not None and t.reasoning_tokens is not None
    assert d.reasoning_tokens < t.reasoning_tokens * REGIME_SEPARATION_MAX_RATIO
    assert check_regime_separation(list(results.values())) is None


@pytest.mark.contract
def test_token_split_reconciles_against_the_runtimes_own_billing(
    results: dict[str, ArmResult],
) -> None:
    """The check on the check (S1's argument, applied per arm).

    The harmony format wraps each channel in structural tokens that are billed and are
    not in the extracted text, so a small POSITIVE residual is expected. A large or
    negative one means the encoding is wrong for this model -- which is the failure a
    lone plausible-looking number would hide.

    **The bound is absolute, not a percentage, and that is the whole point.** The
    wrapper is a fixed handful of tokens per response -- both arms measure exactly +10,
    on 156 billed tokens and on 1489. A percentage bound would pass the long arm and
    fail the short one for the same correct behaviour. A *wrong* encoding, by contrast,
    mis-tokenises the text itself, so its residual grows with the text and blows well
    past a constant -- which is exactly what this must catch.
    """
    for r in results.values():
        c = r.completion
        assert c is not None and c.tokenizer == "o200k_harmony"
        assert c.reasoning_tokens is not None and c.answer_tokens is not None
        assert c.structural_token_residual is not None
        assert 0 <= c.structural_token_residual <= MAX_STRUCTURAL_RESIDUAL, (
            f"{r.strategy}: residual {c.structural_token_residual} against "
            f"{c.completion_tokens} billed -- wrong encoding?"
        )


@pytest.mark.contract
def test_the_direct_arm_emits_no_reasoning_attribute_when_it_has_no_trace() -> None:
    """Absence is encoded as absence, never as an empty string.

    An empty `...message.reasoning` is indistinguishable from "the model thought and
    produced nothing". Arm 1 legitimately has no trace to show, and the analyzer must be
    able to tell the two apart to set `trace_quality` honestly.
    """
    from rlens.llm import Completion
    from rlens.runner.emit import llm_span_attributes

    bare = Completion(
        text="42",
        reasoning="",
        model="gpt-oss:20b",
        finish_reason="stop",
        prompt_tokens=10,
        completion_tokens=2,
        total_tokens=12,
        reasoning_tokens=0,
        answer_tokens=2,
        tokenizer="o200k_harmony",
        structural_token_residual=0,
        budget_bound=False,
        requested_effort="low",
        attempts=1,
    )
    attrs = llm_span_attributes(bare, [{"role": "user", "content": "q"}], TEST_PIN)
    assert "llm.output_messages.0.message.reasoning" not in attrs


# ------------------------------------------------------------------ arm 3 (M1-7)
#: Arm 3's contract is asserted against REAL bank items rather than `probe-01`.
#: `probe-01` exists because arms 1-2 were built before the bank did (M1-6 precedes
#: M1-4); arm 3 has a bank to run against, and using it means this test also proves the
#: committed corpus and the real lookup path work under replay. Note the tools are NOT
#: mocked -- only the model is. So this exercises the loop, both tools, the corpus and the
#: emission path together, with the only non-deterministic part replayed.
REACT_TOOL_ITEM = "mb-08"  # two lookups, three turns -- the fullest loop in the bank
REACT_NO_TOOL_ITEM = "mb-01"  # an `easy` item: one turn, no tools, no turns burned


@pytest.fixture(scope="module")
def react_results() -> dict[str, ArmResult]:
    os.environ["MOCK_LLM"] = "1"
    return {
        item: asyncio.run(run_arm(ARMS["react"], item, "unused under replay", pin=TEST_PIN))
        for item in (REACT_TOOL_ITEM, REACT_NO_TOOL_ITEM)
    }


@pytest.mark.contract
def test_the_react_arm_emits_one_root_chain_with_llm_and_tool_children(
    react_results: dict[str, ArmResult],
) -> None:
    """C4.1: one root CHAIN per arm, LLM spans per model call, TOOL spans per tool call."""
    result = react_results[REACT_TOOL_ITEM]
    roots = [s for s in result.spans if s["parentSpanId"] is None]
    assert len(roots) == 1
    assert roots[0]["attributes"]["openinference.span.kind"] == "CHAIN"

    assert result.react is not None
    kinds = [s["attributes"]["openinference.span.kind"] for s in result.spans]
    # One LLM span per model call and one TOOL span per tool call -- counted against what
    # the loop recorded, so a span the emitter forgot to write cannot pass unnoticed.
    assert kinds.count("LLM") == result.react.turn_count >= 2
    assert kinds.count("TOOL") == result.react.tool_calls_made >= 1
    assert all(s["parentSpanId"] == roots[0]["spanId"] for s in result.spans if s["parentSpanId"])


@pytest.mark.contract
def test_the_react_arm_really_called_its_tools_under_replay(
    react_results: dict[str, ArmResult],
) -> None:
    """The model is replayed; the TOOLS are not. A green test here means the loop fed real
    arguments to the real corpus and got real observations back -- which is the half a
    cassette cannot fake."""
    result = react_results[REACT_TOOL_ITEM]
    assert result.react is not None
    assert result.react.tool_calls_made >= 1
    assert result.react.failed_tool_calls == 0
    tools = [s for s in result.spans if s["attributes"]["openinference.span.kind"] == "TOOL"]
    for span in tools:
        attrs = span["attributes"]
        assert attrs["rlens.tool.ok"] is True
        assert attrs["output.value"].strip()
        assert not attrs["output.value"].startswith("NOT FOUND:")


@pytest.mark.contract
def test_react_tool_spans_use_the_third_party_attribute_names() -> None:
    """Read off `fixtures/spans/langgraph_react_reference.json`, not invented -- ADR-007.

    This asserts the convergence directly: every attribute name our TOOL spans use for
    the tool itself must also appear on the stock LangGraph capture. A private dialect
    would cost C4.2 a second ReAct branch, and B12's "integration, not a rewrite" claim
    is worth nothing if our own trees are the exception to it.
    """
    import json
    import pathlib

    reference = json.loads(
        (
            pathlib.Path(__file__).parent / "fixtures/spans/langgraph_react_reference.json"
        ).read_text()
    )
    ref_spans = reference.get("resourceSpans") or reference
    ref_tool = next(
        s for s in ref_spans if (s.get("attributes") or {}).get("openinference.span.kind") == "TOOL"
    )
    theirs = set(ref_tool["attributes"])

    os.environ["MOCK_LLM"] = "1"
    result = asyncio.run(
        run_arm(ARMS["react"], REACT_TOOL_ITEM, "unused under replay", pin=TEST_PIN)
    )
    ours = next(s for s in result.spans if s["attributes"]["openinference.span.kind"] == "TOOL")
    # Our own metadata is namespaced and is allowed to be ours alone; everything else
    # must be a name their instrumentation also emits.
    shared = {k for k in ours["attributes"] if not k.startswith("rlens.")}
    assert shared <= theirs, f"names we invented: {sorted(shared - theirs)}"
    assert {"tool.name", "input.value", "output.value"} <= shared


@pytest.mark.contract
def test_an_easy_item_terminates_without_burning_turns(
    react_results: dict[str, ArmResult],
) -> None:
    """C4.1's DoD names this explicitly. "An agent that burns 6 turns on an arithmetic
    item is a cost bug that shows up as a latency bug in Month 3.\""""
    result = react_results[REACT_NO_TOOL_ITEM]
    assert result.react is not None
    assert result.react.turn_count == 1
    assert result.react.tool_calls_made == 0
    assert not result.react.max_turns_exhausted
    assert result.trace_quality == "full"
    assert not [s for s in result.spans if s["attributes"]["openinference.span.kind"] == "TOOL"]


@pytest.mark.contract
def test_the_react_arm_carries_reasoning_on_every_turn(
    react_results: dict[str, ArmResult],
) -> None:
    """ADR-007's whole reason for existing, asserted on recorded output rather than
    argued. On a tool-calling turn the visible content is empty and the thought is in
    `reasoning` -- so if this attribute were missing, every ReAct `thought` step C4.2
    produces would be empty and nothing would look broken."""
    result = react_results[REACT_TOOL_ITEM]
    llms = [s for s in result.spans if s["attributes"]["openinference.span.kind"] == "LLM"]
    assert len(llms) >= 2
    for span in llms:
        assert span["attributes"].get("llm.output_messages.0.message.reasoning", "").strip(), (
            f"{span['spanId']} carries no reasoning text"
        )


@pytest.mark.contract
def test_the_react_root_span_carries_the_pin_tuple_and_the_loop_counters(
    react_results: dict[str, ArmResult],
) -> None:
    attrs = react_results[REACT_TOOL_ITEM].spans[0]["attributes"]
    assert attrs["rlens.strategy"] == "react"
    assert attrs["rlens.pin.fingerprint"] == TEST_PIN.fingerprint()
    assert attrs["rlens.pin.digest"] == TEST_PIN.digest
    assert attrs["rlens.deterministic"] is False
    for key in (
        "rlens.react.turns",
        "rlens.react.max_turns",
        "rlens.react.max_turns_exhausted",
        "rlens.react.tool_calls",
        "rlens.react.failed_tool_calls",
    ):
        assert key in attrs, f"the root span does not record {key}"
