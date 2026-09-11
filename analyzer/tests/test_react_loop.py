"""Arm 3's loop control. M1-7's "verify explicitly" list, made executable.

C4.1's DoD for M1-7 names three things to check beyond "it runs": the `max_turns` guard
trips cleanly, an `easy` item where no tool is needed terminates without burning turns, and
a `lookup` miss returns a well-formed negative observation rather than an exception.

All three are tested here against a **scripted provider** rather than cassettes. That is
deliberate: a cassette replays what the model happened to do, and the model does not
reliably produce a six-turn runaway or a tool-name typo on demand. The loop's failure
handling is the part most likely to be wrong and least likely to be exercised by a normal
run, so it is driven directly. The *emission* path is covered against real cassettes in
`test_span_contract.py`.

Owner: M1-7.
"""

from __future__ import annotations

from typing import Any

import pytest
from rlens.llm import Completion, ProviderError
from rlens.runner.react import build_react_spans, run_react
from rlens.versions import GenerationPin

PIN = GenerationPin(
    model="gpt-oss:20b",
    digest="sha256:test",
    quantization="MXFP4",
    runtime="ollama 0.33.3",
    temperature=0.0,
    top_p=1.0,
    seed=20260910,
    reasoning_effort="medium",
)

CORPUS = {"fairhaven_population": "128400", "brightwater_population": "96750"}


def _completion(
    text: str = "", reasoning: str = "thinking", tool_calls: tuple[dict[str, Any], ...] = ()
) -> Completion:
    return Completion(
        text=text,
        reasoning=reasoning,
        model="gpt-oss:20b",
        finish_reason="tool_calls" if tool_calls else "stop",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        reasoning_tokens=5,
        answer_tokens=5,
        tokenizer="o200k_harmony",
        structural_token_residual=10,
        budget_bound=False,
        requested_effort="medium",
        attempts=1,
        tool_calls=tool_calls,
    )


def _tool_call(name: str, arguments: dict[str, Any], call_id: str = "call_1") -> dict[str, Any]:
    return {"id": call_id, "name": name, "arguments": arguments}


def _script(monkeypatch: pytest.MonkeyPatch, completions: list[Any]) -> list[list[dict[str, Any]]]:
    """Install a provider that returns `completions` in order, recording what it was sent.

    Returns the list of message histories, so a test can assert on what the loop actually
    fed back — which is where a ReAct bug hides: the tool result reaching the model in the
    wrong shape looks identical to the model ignoring it.
    """
    seen: list[list[dict[str, Any]]] = []
    calls = iter(completions)

    def fake_generate(messages: list[dict[str, Any]], **kwargs: Any) -> Completion:
        seen.append([dict(m) for m in messages])
        nxt = next(calls)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    monkeypatch.setattr("rlens.runner.react.generate", fake_generate)
    return seen


# ------------------------------------------------------------------ termination
def test_answering_without_a_tool_call_terminates_on_the_first_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C4.1's DoD: an `easy` item, where a ReAct loop has nothing useful to do.

    "An agent that burns 6 turns on an arithmetic item is a cost bug that shows up as a
    latency bug in Month 3" — so this asserts the turn count, not merely the answer.
    """
    _script(monkeypatch, [_completion(text="42")])
    result = run_react("mb-01", "2 + 40?", pin=PIN, corpus=CORPUS)

    assert result.turn_count == 1
    assert result.tool_calls_made == 0
    assert not result.max_turns_exhausted
    assert result.final is not None and result.final.text == "42"


def test_the_loop_feeds_observations_back_and_stops_when_the_model_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),)),
            _completion(text="128400"),
        ],
    )
    result = run_react("mb-09", "look it up", pin=PIN, corpus=CORPUS)

    assert result.turn_count == 2
    assert result.tool_calls_made == 1
    assert result.invocations[0].observation == "128400"
    assert result.invocations[0].ok

    # The second request must carry the assistant's tool_calls AND a matching tool
    # message. A tool result delivered without its `tool_call_id`, or without the
    # assistant turn that asked for it, is silently ignored by the runtime -- and the
    # symptom is a model that "won't use the tool result", not an error.
    second = seen[1]
    assistant = next(m for m in second if m["role"] == "assistant")
    tool_msg = next(m for m in second if m["role"] == "tool")
    assert assistant["tool_calls"][0]["function"]["name"] == "lookup"
    assert tool_msg["tool_call_id"] == assistant["tool_calls"][0]["id"]
    assert tool_msg["content"] == "128400"


# ------------------------------------------------------------------ the max_turns guard
def test_the_max_turns_guard_trips_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model that never stops calling tools must stop the LOOP, not the run.

    C4.1: a degraded arm emits a partial trace rather than failing. An agent that cannot
    finish in six turns is an observation about the agent.
    """
    forever = [
        _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),))
        for _ in range(20)
    ]
    _script(monkeypatch, forever)
    result = run_react("mb-08", "loop forever", pin=PIN, corpus=CORPUS, max_turns=6)

    assert result.max_turns_exhausted
    assert result.turn_count == 6, "the cap is the number of MODEL CALLS, not tool calls"
    assert result.tool_calls_made == 6
    assert result.failed_reason is None, "exhausting the cap is not a provider failure"


def test_max_turns_is_configurable_and_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    _script(
        monkeypatch,
        [_completion(tool_calls=(_tool_call("lookup", {"query": "x"}),)) for _ in range(10)],
    )
    result = run_react("mb-08", "loop", pin=PIN, corpus=CORPUS, max_turns=2)
    assert result.turn_count == 2
    assert result.max_turns_exhausted


# ------------------------------------------------------------------ bad calls
def test_a_lookup_miss_becomes_an_observation_and_the_loop_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C4.1's DoD, exactly: "a lookup miss returns a well-formed negative observation
    rather than an exception". The point of feeding it back is that the model recovers --
    so the recovery is what is asserted, not just the absence of a traceback."""
    seen = _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "population of Fairhaven"}),)),
            _completion(
                tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}, "c2"),)
            ),
            _completion(text="128400"),
        ],
    )
    result = run_react("mb-09", "look it up", pin=PIN, corpus=CORPUS)

    assert result.turn_count == 3
    assert result.tool_calls_made == 2
    assert result.failed_tool_calls == 1
    assert not result.invocations[0].ok
    assert result.invocations[0].observation.startswith("NOT FOUND:")
    # The negative observation must actually reach the model, and must name the keys --
    # that is what makes the second turn recoverable rather than a repeat of the first.
    miss_text = next(m for m in seen[1] if m["role"] == "tool")["content"]
    assert "fairhaven_population" in miss_text
    assert result.invocations[1].ok


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("lookup", {}),  # missing required argument
        ("calculator", {"expression": "1/0"}),  # a named arithmetic rejection
        ("calculator", {"_raw": "not json"}),  # arguments llm.py could not parse
        ("search_the_web", {"q": "x"}),  # a tool we do not have
    ],
)
def test_every_shape_of_bad_call_is_an_observation_not_an_exception(
    monkeypatch: pytest.MonkeyPatch, name: str, arguments: dict[str, Any]
) -> None:
    _script(
        monkeypatch,
        [_completion(tool_calls=(_tool_call(name, arguments),)), _completion(text="recovered")],
    )
    result = run_react("mb-08", "try it", pin=PIN, corpus=CORPUS)

    assert result.turn_count == 2
    assert result.failed_tool_calls == 1
    assert result.invocations[0].observation.strip()
    assert result.final is not None and result.final.text == "recovered"


def test_several_tool_calls_in_one_turn_are_all_executed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A turn may request more than one call. Executing only the first would look like the
    model ignoring its own second request, and the trace would not say otherwise."""
    _script(
        monkeypatch,
        [
            _completion(
                tool_calls=(
                    _tool_call("lookup", {"query": "fairhaven_population"}, "a"),
                    _tool_call("lookup", {"query": "brightwater_population"}, "b"),
                )
            ),
            _completion(text="31650"),
        ],
    )
    result = run_react("mb-08", "both", pin=PIN, corpus=CORPUS)
    assert result.tool_calls_made == 2
    assert [i.observation for i in result.invocations] == ["128400", "96750"]


# ------------------------------------------------------------------ provider failure
def test_a_provider_failure_on_the_first_turn_leaves_no_trace_and_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _script(monkeypatch, [ProviderError("connection refused")])
    result = run_react("mb-08", "x", pin=PIN, corpus=CORPUS)
    assert result.turn_count == 0
    assert result.failed_reason == "connection refused"


def test_a_provider_failure_mid_loop_keeps_the_turns_that_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The partial trace is the point. Discarding two good turns because the third failed
    would throw away the only record of what the agent had worked out."""
    _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),)),
            ProviderError("timeout"),
        ],
    )
    result = run_react("mb-08", "x", pin=PIN, corpus=CORPUS)
    assert result.turn_count == 1
    assert result.tool_calls_made == 1
    assert result.failed_reason == "timeout"


# ------------------------------------------------------------------ the span tree
def test_the_span_tree_interleaves_llm_and_tool_spans_in_execution_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`rlens.seq` carries the order, because the serialised tree has no timestamps and
    C3.2's `step_id` embeds an ordinal. Sorting by span id would work until turn 10 sorted
    before turn 2 -- and reordering steps after labelling begins is Hazard 1."""
    _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),)),
            _completion(tool_calls=(_tool_call("calculator", {"expression": "128400/4"}, "c2"),)),
            _completion(text="32100"),
        ],
    )
    result = run_react("mb-08", "x", pin=PIN, corpus=CORPUS)
    spans = build_react_spans(result, "mb-08", PIN, trace_quality="full")

    kinds = [s["attributes"]["openinference.span.kind"] for s in spans]
    assert kinds == ["CHAIN", "LLM", "TOOL", "LLM", "TOOL", "LLM"]

    children = [s for s in spans if s["parentSpanId"] is not None]
    seqs = [s["attributes"]["rlens.seq"] for s in children]
    assert seqs == sorted(seqs) == list(range(len(children))), "seq must be dense and ordered"

    # TOOL spans are SIBLINGS of the LLM spans under the root, matching the stock
    # LangGraph capture -- that is what keeps one segmenter path for our trees and
    # third-party trees. See ADR-007.
    root = spans[0]
    assert all(s["parentSpanId"] == root["spanId"] for s in children)


def test_the_root_span_records_what_the_loop_did(monkeypatch: pytest.MonkeyPatch) -> None:
    _script(
        monkeypatch,
        [_completion(tool_calls=(_tool_call("lookup", {"query": "nope"}),)) for _ in range(6)],
    )
    result = run_react("mb-08", "x", pin=PIN, corpus=CORPUS, max_turns=6)
    spans = build_react_spans(result, "mb-08", PIN, trace_quality="partial")
    attrs = spans[0]["attributes"]

    assert attrs["rlens.react.turns"] == 6
    assert attrs["rlens.react.max_turns"] == 6
    assert attrs["rlens.react.max_turns_exhausted"] is True
    assert attrs["rlens.react.tool_calls"] == 6
    assert attrs["rlens.react.failed_tool_calls"] == 6
    assert attrs["rlens.trace_quality"] == "partial"


def test_tool_spans_carry_the_names_a_stock_langgraph_trace_carries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read off `fixtures/spans/langgraph_react_reference.json`, not invented. ADR-007:
    a private dialect would cost C4.2 a second ReAct branch, and B12's "integration, not
    a rewrite" claim is worth nothing if our own trees are the exception."""
    _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),)),
            _completion(text="128400"),
        ],
    )
    result = run_react("mb-09", "x", pin=PIN, corpus=CORPUS)
    spans = build_react_spans(result, "mb-09", PIN, trace_quality="full")
    tool = next(s for s in spans if s["attributes"]["openinference.span.kind"] == "TOOL")
    attrs = tool["attributes"]

    assert tool["name"] == "lookup", "the span is NAMED for the tool, as in the reference"
    assert attrs["tool.name"] == "lookup"
    assert attrs["tool.description"].strip()
    assert "fairhaven_population" in attrs["input.value"]
    assert attrs["output.value"] == "128400"
    assert attrs["output.mime_type"] == "text/plain"
    assert attrs["rlens.tool.ok"] is True


def test_the_llm_spans_carry_the_history_they_were_actually_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An arm-3 LLM span with an empty input would be the only span in the system that
    lies about having had a prompt -- and a derailed loop is unreadable without it."""
    _script(
        monkeypatch,
        [
            _completion(tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),)),
            _completion(text="128400"),
        ],
    )
    result = run_react("mb-09", "look up the population", pin=PIN, corpus=CORPUS)
    spans = build_react_spans(result, "mb-09", PIN, trace_quality="full")
    llm = [s for s in spans if s["attributes"]["openinference.span.kind"] == "LLM"]

    first = llm[0]["attributes"]
    assert first["llm.input_messages.0.message.role"] == "system"
    assert first["llm.input_messages.1.message.content"] == "look up the population"

    # The second call's history includes the assistant turn that asked for the tool and
    # the tool result that came back.
    second = llm[1]["attributes"]
    # INPUT messages only: the span also carries `llm.output_messages.0.message.role`,
    # and a filter on `.message.role` alone picks that up too.
    roles = [
        second[f"llm.input_messages.{i}.message.role"]
        for i in range(len([k for k in second if k.startswith("llm.input_messages.")]) // 2)
    ]
    assert roles == ["system", "user", "assistant", "tool"]
    assert "lookup" in second["llm.input_messages.2.message.tool_calls"]


def test_reasoning_reaches_every_turns_span(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole reason arm 3 is not LangGraph (ADR-007). On a tool-calling turn this
    model returns an EMPTY `content` and puts the thought in `reasoning` -- the field
    LangChain drops. If it did not reach the span, every ReAct `thought` step would be
    empty and nothing would look broken."""
    _script(
        monkeypatch,
        [
            _completion(
                text="",
                reasoning="We need the population. Use lookup.",
                tool_calls=(_tool_call("lookup", {"query": "fairhaven_population"}),),
            ),
            _completion(text="128400", reasoning="Now subtract."),
        ],
    )
    result = run_react("mb-09", "x", pin=PIN, corpus=CORPUS)
    spans = build_react_spans(result, "mb-09", PIN, trace_quality="full")
    llm = [s for s in spans if s["attributes"]["openinference.span.kind"] == "LLM"]

    for span in llm:
        text = span["attributes"].get("llm.output_messages.0.message.reasoning")
        assert text, f"{span['spanId']} carries no reasoning text"
    assert llm[0]["attributes"]["llm.output_messages.0.message.content"] == "", (
        "the tool-calling turn's visible content really is empty -- that is the finding"
    )
