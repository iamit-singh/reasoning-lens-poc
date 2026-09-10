"""S2 -- OTEL / OpenInference attribute shape, via a stock LangGraph agent. Task M1-2, W2.

The question: **which attribute names actually arrive**, so C3.1's mapping table is real
rather than aspirational. C3.1 is written as a precedence chain precisely because nobody
had yet checked which of its candidates a stock instrumentation emits. Writing
`ingest/otel.py` against it unchecked means shipping three fallback branches, two of them
dead code, and discovering in W3 that the live attribute is a fourth name nobody listed.

Two rules this harness exists to hold:

  1. **The agent is stock.** `langgraph.prebuilt.create_react_agent` with the
     OpenInference LangChain instrumentor, unmodified. The analyzer has never seen it and
     must never be adapted to. That is what makes the captured fixture B12's
     "integration, not a rewrite" evidence (C7.1) rather than a convenience file.
  2. **Absence is a finding.** A C3.1 row whose attributes do not arrive is reported
     ABSENT with whatever did arrive in its place. A spike that only records hits cannot
     distinguish "confirmed" from "not looked for".

Usage
-----
    make spike-s2                       # capture + delta table, using .env
    make spike-s2 ARGS="--no-write"     # print the delta, commit nothing

Writes the reference span fixture to
`analyzer/tests/fixtures/spans/langgraph_react_reference.json` and the raw capture to
`docs/spikes/S2-raw/`.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = REPO / "analyzer/tests/fixtures/spans/langgraph_react_reference.json"
RAW_DIR = REPO / "docs/spikes/S2-raw"

# The probe. One tool call is mandatory (the price is not derivable), which is what makes
# the TOOL span and the tool-result rows of C3.1 observable at all. Same arithmetic family
# as the S1 probe so the two spikes' traces are comparable by eye.
PROBE = (
    "A warehouse ships cartons of 12 items under SKU CTN-12. Look up the unit price of "
    "one carton of SKU CTN-12 with the tool provided -- do not guess it -- then tell me "
    "the total price of 7 cartons. Give the final number on its own last line."
)
# The SKU is stated. An under-specified probe makes the model ask a clarifying question
# instead of calling the tool, and the TOOL span never exists -- which reads in the delta
# as "tool attributes absent" when the truth is "never exercised". S6 already established
# this model calls tools 20/20, so a missing TOOL span here would be the harness's fault,
# not a finding.

# ---------------------------------------------------------------------------- C3.1
# The nine rows of the input contract, verbatim, in their stated precedence order.
# `patterns` are fnmatch globs: C3.1 writes `llm.output_messages.*.message.reasoning`
# with a wildcard, and the wildcard is part of the claim being tested.
#
# `alternatives` is what separates CORRECTED from ABSENT, and the distinction is the whole
# value of this spike. A row whose claimed name misses but whose concept arrives under
# another name costs a one-line mapping change in M1-6. A row whose concept does not
# arrive at all costs an architectural decision. Collapsing both into "not found" would
# hand M1-6 a list of problems with no idea which ones are cheap.
C31_ROWS: list[dict[str, Any]] = [
    {
        "concept": "Span kind",
        "patterns": ["openinference.span.kind", "gen_ai.operation.name"],
        "alternatives": [],
        "used_for": "routing LLM / TOOL / CHAIN / AGENT",
        "required": True,
    },
    {
        "concept": "Model id",
        "patterns": ["gen_ai.request.model", "gen_ai.response.model"],
        "alternatives": ["llm.model_name", "llm.provider", "llm.system"],
        "used_for": "MODEL_PIN verification, cost",
        "required": True,
    },
    {
        "concept": "Thinking / reasoning text",
        "patterns": [
            "gen_ai.completion.reasoning",
            "llm.output_messages.*.message.reasoning",
            "*thinking*",
        ],
        "alternatives": [],
        "used_for": "segmentation input for arms 1-2",
        "required": True,
    },
    {
        "concept": "Answer text",
        "patterns": ["gen_ai.completion.*.content", "llm.output_messages.*.message.content"],
        "alternatives": ["output.value"],
        "used_for": "accuracy check, consistency check",
        "required": True,
    },
    {
        "concept": "Prompt text",
        "patterns": ["gen_ai.prompt.*.content", "llm.input_messages.*"],
        "alternatives": ["input.value"],
        "used_for": "judge context",
        "required": True,
    },
    {
        "concept": "Tool call",
        "patterns": ["gen_ai.tool.name", "tool.name", "tool.parameters"],
        "alternatives": [
            "llm.output_messages.*.message.tool_calls.*.tool_call.function.name",
            "llm.output_messages.*.message.tool_calls.*.tool_call.function.arguments",
            "tool.description",
            "llm.tools.*.tool.json_schema",
        ],
        "used_for": "ReAct step boundaries",
        "required": True,
    },
    {
        "concept": "Tool result",
        "patterns": ["output.value", "*.events.*"],
        "alternatives": ["llm.input_messages.*.message.tool_call_id"],
        "used_for": "observation steps",
        "required": True,
    },
    {
        "concept": "Tokens",
        "patterns": [
            "gen_ai.usage.input_tokens",
            "gen_ai.usage.output_tokens",
            "gen_ai.usage.reasoning_tokens",
        ],
        "alternatives": [
            "llm.token_count.prompt",
            "llm.token_count.completion",
            "llm.token_count.total",
        ],
        "used_for": "cost-of-thought (B4 #7), cost line",
        "required": True,
    },
    {
        "concept": "Timing",
        "patterns": ["__span.startTime", "__span.endTime"],
        "alternatives": [],
        "used_for": "latency metrics",
        "required": True,
    },
]

# Where reasoning text could plausibly hide if C3.1's three candidates all miss. Searched
# by substring across every attribute NAME, so a fourth name nobody listed still surfaces.
REASONING_HINTS = ("reasoning", "thinking", "thought", "analysis", "cot", "scratchpad")


# ---------------------------------------------------------------------------- the agent
def build_and_run(base_url: str, model: str, timeout: int) -> tuple[list[dict[str, Any]], str]:
    """Run one unmodified LangGraph ReAct agent under OpenInference instrumentation.

    Everything provider-shaped stays inside this function. Nothing here is imported by
    the analyzer -- C2.2 confines provider SDK symbols to `rlens.llm` and
    `rlens.ingest.otel`, and a spike that leaked them into the package would be the
    boundary contract's first real violation.
    """
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    LangChainInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True)

    @tool
    def carton_unit_price(sku: str) -> str:
        """Look up the unit price in USD of one carton for the given SKU."""
        return json.dumps({"sku": sku, "unit_price_usd": 43.5, "currency": "USD"})

    llm = ChatOpenAI(
        base_url=base_url,
        api_key=os.environ.get("LOCAL_API_KEY", "ollama"),
        model=model,
        temperature=float(os.environ.get("GEN_TEMPERATURE", "0")),
        timeout=timeout,
    )
    agent = create_react_agent(llm, [carton_unit_price])
    result = agent.invoke({"messages": [("user", PROBE)]})

    final = ""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    if messages:
        content = getattr(messages[-1], "content", "")
        final = content if isinstance(content, str) else json.dumps(content)

    LangChainInstrumentor().uninstrument()
    return [_span_to_dict(s) for s in exporter.get_finished_spans()], final


def _span_to_dict(span: Any) -> dict[str, Any]:
    """Serialise one ReadableSpan into the OTLP-shaped JSON the analyzer will read.

    Field names follow the OTLP JSON encoding (`startTime`/`endTime`, hex ids) rather than
    the Python SDK's snake_case, because the analyzer's real input is an exported span
    tree, not an in-process object.
    """
    ctx = span.get_span_context()
    parent = span.parent
    return {
        "name": span.name,
        "traceId": format(ctx.trace_id, "032x"),
        "spanId": format(ctx.span_id, "016x"),
        "parentSpanId": format(parent.span_id, "016x") if parent else None,
        "kind": str(span.kind),
        "startTime": span.start_time,
        "endTime": span.end_time,
        "status": {
            "code": span.status.status_code.name,
            "message": span.status.description,
        },
        "attributes": {k: _jsonable(v) for k, v in dict(span.attributes or {}).items()},
        "events": [
            {
                "name": e.name,
                "timestamp": e.timestamp,
                "attributes": {k: _jsonable(v) for k, v in dict(e.attributes or {}).items()},
            }
            for e in span.events
        ],
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


# ---------------------------------------------------------------------------- the delta
def observed_names(spans: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Every attribute name that arrived, mapped to the span names carrying it.

    Span-level fields are prefixed `__span.` and event attributes `__event.<name>.` so
    that C3.1's non-attribute rows -- timing, and tool results that arrive as span events
    -- can be checked by the same matcher as everything else.
    """
    names: dict[str, list[str]] = {}

    def record(key: str, span_name: str) -> None:
        names.setdefault(key, [])
        if span_name not in names[key]:
            names[key].append(span_name)

    for span in spans:
        for key in ("startTime", "endTime", "name", "spanId", "parentSpanId"):
            record(f"__span.{key}", span["name"])
        for key in span["attributes"]:
            record(key, span["name"])
        for event in span["events"]:
            for key in event["attributes"]:
                record(f"__event.{event['name']}.{key}", span["name"])
    return names


def build_delta(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark every C3.1 row confirmed, corrected or absent. Never silently skipped."""
    names = observed_names(spans)

    def matching(patterns: list[str]) -> list[str]:
        hits: list[str] = []
        for pattern in patterns:
            hits += [n for n in names if fnmatch.fnmatch(n, pattern) and n not in hits]
        return sorted(hits)

    rows = []
    for row in C31_ROWS:
        claimed_hits = matching(row["patterns"])
        alt_hits = matching(row["alternatives"]) if not claimed_hits else []
        if claimed_hits:
            verdict = "CONFIRMED"
        elif alt_hits:
            verdict = "CORRECTED"
        else:
            verdict = "ABSENT"
        rows.append(
            {
                "concept": row["concept"],
                "claimed": row["patterns"],
                "observed": claimed_hits or alt_hits,
                "verdict": verdict,
                "used_for": row["used_for"],
            }
        )
    return rows


def find_reasoning(spans: list[dict[str, Any]]) -> dict[str, Any]:
    """Hunt for reasoning text under ANY name, not just C3.1's three candidates.

    This is the row the architecture turns on. S1 established that the local runtime
    returns the raw trace in a `reasoning` field on the message; whether that field
    survives LangChain's message model and the instrumentor's serialisation into a span
    attribute is a different question, and it is the one that decides whether M1-6 has to
    emit reasoning itself.
    """
    names = observed_names(spans)
    by_name = sorted(n for n in names if any(h in n.lower() for h in REASONING_HINTS))

    # A hit on the attribute NAME is not the finding -- the text has to actually be there.
    # An `...message.reasoning` key holding "" is an absent trace with a present name.
    carrying: list[dict[str, Any]] = []
    for span in spans:
        for key, value in span["attributes"].items():
            if (
                any(h in key.lower() for h in REASONING_HINTS)
                and isinstance(value, str)
                and value.strip()
            ):
                carrying.append({"span": span["name"], "attribute": key, "chars": len(value)})

    # Reasoning may also be buried inside a serialised JSON blob (output.value and
    # friends), which is a materially worse contract than a first-class attribute but is
    # still recoverable. Distinguishing the two is the point.
    buried: list[dict[str, Any]] = []
    for span in spans:
        for key, value in span["attributes"].items():
            if not isinstance(value, str) or key in {c["attribute"] for c in carrying}:
                continue
            for hint in ('"reasoning"', "'reasoning'", "reasoning_content", "<think>"):
                if hint in value:
                    buried.append({"span": span["name"], "attribute": key, "marker": hint})
                    break

    return {
        "attribute_names_matching": by_name,
        "attributes_carrying_text": carrying,
        "buried_in_serialised_blob": buried,
        "recoverable_as_first_class_attribute": bool(carrying),
    }


# ---------------------------------------------------------------------------- control
def control_direct_call(base_url: str, model: str, timeout: int) -> dict[str, Any]:
    """The same request, made directly over HTTP, bypassing LangChain entirely.

    This is the control, and without it the spike cannot name the culprit. If reasoning
    text is missing from the spans there are three candidates -- the runtime did not send
    it, LangChain dropped it, or the instrumentor did not serialise it -- and they call for
    three different fixes. The direct call settles the first one, which is the only one
    that would put the whole local-generation decision (ADR-001) back in question.
    """
    import json as _json
    import urllib.request

    payload = {
        "model": model,
        "temperature": float(os.environ.get("GEN_TEMPERATURE", "0")),
        "messages": [{"role": "user", "content": PROBE}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "carton_unit_price",
                    "description": "Look up the unit price in USD of one carton for the given SKU.",
                    "parameters": {
                        "type": "object",
                        "properties": {"sku": {"type": "string"}},
                        "required": ["sku"],
                    },
                },
            }
        ],
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=_json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LOCAL_API_KEY', 'ollama')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = _json.load(resp)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    msg = data["choices"][0]["message"]
    text = msg.get("reasoning") or ""
    return {
        "ok": True,
        "message_keys": sorted(msg.keys()),
        "reasoning_field_present": "reasoning" in msg,
        "reasoning_chars": len(text),
        "tool_calls": len(msg.get("tool_calls") or []),
        "usage": data.get("usage", {}),
    }


# ---------------------------------------------------------------------------- report
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="S2 -- OTEL/OpenInference attribute shape")
    ap.add_argument(
        "--base-url", default=os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")
    )
    ap.add_argument("--model", default=os.environ.get("LOCAL_MODEL", "gpt-oss:20b"))
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("ARM_TIMEOUT_S", "180")))
    ap.add_argument("--no-write", action="store_true", help="print the delta, write nothing")
    args = ap.parse_args(argv)

    print(f"S2 -- stock LangGraph ReAct agent against {args.model} at {args.base_url}")
    try:
        spans, final = build_and_run(args.base_url, args.model, args.timeout)
    except Exception as exc:  # a spike reports its failure, it does not raise it
        print(f"\nFAILED to run the agent: {type(exc).__name__}: {exc}")
        print("The runtime must be serving (`make serve-local`) and the model pulled.")
        return 2

    if not spans:
        print("\nFAILED: the agent ran but no spans were exported -- instrumentation is not live.")
        return 2

    delta = build_delta(spans)
    reasoning = find_reasoning(spans)
    names = observed_names(spans)

    print(f"\nSpans captured: {len(spans)}")
    for span in spans:
        kind = span["attributes"].get("openinference.span.kind", "?")
        print(f"  {span['name']:<28} kind={kind:<10} attrs={len(span['attributes'])}")

    print("\nC3.1 delta")
    print(f"  {'Concept':<28} {'Verdict':<10} Observed")
    for row in delta:
        obs = ", ".join(row["observed"][:2]) or "--"
        if len(row["observed"]) > 2:
            obs += f" (+{len(row['observed']) - 2})"
        print(f"  {row['concept']:<28} {row['verdict']:<10} {obs}")

    absent = [r["concept"] for r in delta if r["verdict"] == "ABSENT"]
    corrected = [r["concept"] for r in delta if r["verdict"] == "CORRECTED"]
    first_class = reasoning["recoverable_as_first_class_attribute"]
    print(f"\nReasoning text as a first-class attribute: {first_class}")
    for c in reasoning["attributes_carrying_text"]:
        print(f"  {c['attribute']} on {c['span']} -- {c['chars']} chars")
    for b in reasoning["buried_in_serialised_blob"]:
        print(f"  buried: {b['marker']} inside {b['attribute']} on {b['span']}")

    control = control_direct_call(args.base_url, args.model, args.timeout)
    print("\nControl -- the same request, direct over HTTP, no LangChain")
    if not control["ok"]:
        print(f"  control call FAILED: {control['error']} -- attribution below is unproven")
    else:
        print(f"  message keys: {', '.join(control['message_keys'])}")
        present, chars = control["reasoning_field_present"], control["reasoning_chars"]
        print(f"  reasoning field: {present}, {chars} chars")

    if control.get("ok") and control["reasoning_chars"] > 0 and not first_class:
        attribution = "LangChain: the runtime returns reasoning, the span tree does not carry it"
    elif control.get("ok") and control["reasoning_chars"] == 0:
        attribution = "runtime: it did not return reasoning for this call shape at all"
    else:
        attribution = "none needed -- reasoning reached a span attribute"
    print(f"  attribution: {attribution}")

    record = {
        "spike": "S2",
        "task": "M1-2",
        "model": args.model,
        "base_url": args.base_url,
        "versions": _versions(),
        "span_count": len(spans),
        "final_answer": final,
        "delta": delta,
        "reasoning": reasoning,
        "control_direct_call": control,
        "reasoning_loss_attributed_to": attribution,
        "all_attribute_names": sorted(names),
    }

    if not args.no_write:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps({"resourceSpans": spans}, indent=2, sort_keys=True) + "\n")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        (RAW_DIR / "s2-record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"\nfixture -> {FIXTURE.relative_to(REPO)}")
        print(f"record  -> {(RAW_DIR / 's2-record.json').relative_to(REPO)}")

    if corrected:
        print(f"\nCORRECTED rows (concept arrives, name differs): {', '.join(corrected)}")
    if absent:
        print(f"\nABSENT rows: {', '.join(absent)}")
        print("Each one needs an entry in the S2 delta table with an action, not a shrug.")
    if not reasoning["recoverable_as_first_class_attribute"]:
        print(
            "\n*** Reasoning text does not arrive as its own span attribute. Per M1-2's "
            "'On failure' clause this is an I1 question: the fix is emission-side in M1-6, "
            "not an ingest-side workaround. ***"
        )
    return 0


def _versions() -> dict[str, str]:
    import importlib.metadata as md

    out = {}
    for pkg in (
        "langgraph",
        "langchain-core",
        "langchain-openai",
        "openinference-instrumentation-langchain",
        "opentelemetry-sdk",
    ):
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "absent"
    return out


if __name__ == "__main__":
    sys.exit(main())
