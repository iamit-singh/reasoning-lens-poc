"""The S2 reference capture, guarded. Fixture owned by M1-2; ingest assertions by M1-6.

C7.1 names `langgraph_react_reference.json` as B12's "integration, not a rewrite"
evidence: a span tree from a stock LangGraph agent the analyzer has never seen. This
module protects the two things that make it evidence rather than a convenience file --
that it is shaped like a real exported tree, and that the attribute names ADR-002 decided
against are the names actually in it.

**These tests deliberately do not import `rlens.ingest.otel`.** The mapping lands with
M1-6; asserting on it now would be building ahead of the plan's ordering. What is here is
the half that is knowable today: what the capture contains.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

FIXTURE = pathlib.Path(__file__).parent / "fixtures/spans/langgraph_react_reference.json"

# The reasoning-attribute names S2 searched for. Kept as a tuple rather than inlined
# because two tests need the same list and they must not drift apart.
REASONING_HINTS = ("reasoning", "thinking", "thought", "scratchpad")


@pytest.fixture(scope="module")
def spans() -> list[dict[str, Any]]:
    return list(json.loads(FIXTURE.read_text())["resourceSpans"])


def _attr_names(spans: list[dict[str, Any]]) -> set[str]:
    return {k for s in spans for k in s["attributes"]}


@pytest.mark.contract
def test_capture_is_a_well_formed_tree(spans: list[dict[str, Any]]) -> None:
    """Every span resolves: one trace, one root, and no parent pointing outside the set."""
    assert len(spans) == 15, "the S2 capture is 15 spans; a different count is a re-capture"
    ids = {s["spanId"] for s in spans}
    assert len(ids) == len(spans), "duplicate span ids"
    assert len({s["traceId"] for s in spans}) == 1, "the capture must be a single trace"

    roots = [s for s in spans if s["parentSpanId"] is None]
    assert len(roots) == 1, f"expected exactly one root span, got {len(roots)}"
    for s in spans:
        if s["parentSpanId"] is not None:
            assert s["parentSpanId"] in ids, f"{s['name']} parents a span outside the capture"
        assert s["endTime"] >= s["startTime"], f"{s['name']} ends before it starts"


@pytest.mark.contract
def test_the_agent_actually_exercised_the_paths_the_delta_reports_on(
    spans: list[dict[str, Any]],
) -> None:
    """An unexercised path reads exactly like a missing one.

    S2's first run under-specified the probe, the model asked a clarifying question
    instead of calling the tool, and the delta reported the tool rows as absent when they
    were merely never reached. This test is that mistake, made permanent as a check: if a
    re-capture produces no TOOL span, the delta's tool rows mean nothing.
    """
    kinds = [s["attributes"].get("openinference.span.kind") for s in spans]
    assert "TOOL" in kinds, "no TOOL span: the tool rows of the S2 delta are unexercised"
    assert kinds.count("LLM") >= 2, "a ReAct loop that called a tool has at least two LLM turns"
    assert "AGENT" in kinds


@pytest.mark.contract
def test_openinference_namespace_is_what_arrives(spans: list[dict[str, Any]]) -> None:
    """ADR-002: the live namespace is `llm.*`/`openinference.*`, and `gen_ai.*` is dead.

    C3.1 listed a `gen_ai.*` candidate in five rows. If any of them ever starts arriving,
    ADR-002's decision to *delete* those branches rather than keep them as fallbacks is
    the thing that needs revisiting -- so it fails here rather than going unnoticed.
    """
    names = _attr_names(spans)
    assert not [n for n in names if n.startswith("gen_ai.")], (
        "a gen_ai.* attribute now arrives -- re-run `make spike-s2` and amend ADR-002"
    )
    for expected in (
        "openinference.span.kind",
        "llm.model_name",
        "llm.output_messages.0.message.content",
        "llm.token_count.completion",
        "tool.name",
    ):
        assert expected in names, f"ADR-002 maps {expected}, and the capture no longer has it"


@pytest.mark.contract
def test_tool_results_arrive_as_attributes_not_span_events(spans: list[dict[str, Any]]) -> None:
    """C3.1 offered span events for tool results; the capture has none at all."""
    assert sum(len(s["events"]) for s in spans) == 0
    tool_spans = [s for s in spans if s["attributes"].get("openinference.span.kind") == "TOOL"]
    assert all("output.value" in s["attributes"] for s in tool_spans)


@pytest.mark.contract
def test_reasoning_text_is_absent_and_stays_a_detected_change(
    spans: list[dict[str, Any]],
) -> None:
    """The third-party tree carries no reasoning text. This asserts the *finding*, not a wish.

    S2 established that `langchain_openai.ChatOpenAI` drops the runtime's `reasoning`
    field, which is why ADR-002 moves emission into the runner. If a dependency upgrade
    fixes that upstream, this test fails -- and that failure is the good outcome: it means
    ADR-002's emission work may no longer be needed, and the decision should be re-read
    against a fresh capture rather than carried forward out of habit.

    It is not asserting that reasoning *should* be missing. It is asserting that the day it
    stops being missing, somebody finds out.
    """
    for span in spans:
        for key, value in span["attributes"].items():
            if any(h in key.lower() for h in REASONING_HINTS):
                assert not (isinstance(value, str) and value.strip()), (
                    f"reasoning text now arrives at {key} -- re-run `make spike-s2`, "
                    "and re-read ADR-002 before doing anything else"
                )
        blob = span["attributes"].get("output.value")
        if isinstance(blob, str):
            assert '"reasoning"' not in blob and "<think>" not in blob, (
                f"reasoning is now serialised inside output.value on {span['name']} -- "
                "re-run `make spike-s2` and amend ADR-002"
            )
