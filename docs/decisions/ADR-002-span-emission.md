# ADR-002 — The runner emits reasoning text; C3.1's `gen_ai.*` namespace is dropped

| | |
| --- | --- |
| **Status** | **Accepted** — 10 Sep 2026 (W2) |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | Plan §C3.1 (the input contract's attribute mapping table) |
| **Evidence** | [S2 — OTEL/OpenInference attribute shape](../spikes/S2-otel.md) · `analyzer/tests/fixtures/spans/langgraph_react_reference.json` |
| **Owner of the change** | M1-6 (W2) |

## Context

C3.1 specifies the analyzer's input as a span tree with a nine-row attribute mapping,
written as precedence chains because nobody had yet checked which candidates a real
instrumentation emits. §4.1 of the Month-1 breakdown made S2 a precondition of M1-6 for
exactly this reason.

S2 ran a stock LangGraph ReAct agent under the stock OpenInference instrumentor and
compared what arrived. Two things came back.

**1. The namespace is wrong.** Not one `gen_ai.*` attribute arrives — across 15 spans,
zero. C3.1 was written against the OTEL GenAI semantic conventions; the live
instrumentation is OpenInference, which emits `llm.*` / `openinference.*` and does not
dual-write. Five of the nine rows list a `gen_ai.*` candidate; all five are dead.

**2. Reasoning text does not reach the span tree at all.** Not summarised, not truncated,
not buried in a serialised blob — absent, under every name searched. The control isolates
where it is lost:

| Path | `reasoning` present? |
| --- | --- |
| Direct HTTP to the local runtime, identical messages and tools | **yes — 173 chars** |
| Through `langchain_openai.ChatOpenAI` → instrumentor → span | **no** |

`ChatOpenAI` does not map the runtime's non-standard `reasoning` field onto `AIMessage`, so
it is discarded before the instrumentor sees it. The instrumentor is faithful; the message
it serialises no longer contains the trace.

**This threatens I1**, the invariant the architecture rests on: *the analyzer is a
standalone package whose only input is a span tree.* Arms 1–2 segment reasoning text. If
that text is not in the tree, the analyzer must either reach outside its input — which is
the one thing I1 forbids — or receive a tree that contains it.

## Decision

### 1. `ingest/otel.py` reads the OpenInference namespace. The `gen_ai.*` candidates are deleted, not demoted.

| Concept | Read | Was claimed |
| --- | --- | --- |
| Span kind | `openinference.span.kind` | + `gen_ai.operation.name` |
| Model id | `llm.model_name` | `gen_ai.request.model`, `gen_ai.response.model` |
| Answer text | `llm.output_messages.*.message.content` | + `gen_ai.completion.*.content` |
| Prompt text | `llm.input_messages.*.message.*` | + `gen_ai.prompt.*.content` |
| Tool call | `tool.name` + `llm.output_messages.*.message.tool_calls.*.tool_call.function.*` | + `gen_ai.tool.name`, `tool.parameters` |
| Tool result | `output.value` on TOOL spans | + span events |
| Tokens | `llm.token_count.{prompt,completion,total}` | `gen_ai.usage.{input,output,reasoning}_tokens` |

Deleted rather than kept as a fallback, deliberately. A fallback branch that has been
measured never to fire is dead code that reads as diligence — it will be maintained,
type-checked and reviewed forever, and it will never once run. **`tool.parameters` and the
span-events branch for tool results go the same way: neither exists in the capture.** If a
second instrumentation is ever added, its names get added then, against a capture.

### 2. The runner emits reasoning text as a first-class span attribute.

M1-6 sets, on the LLM span it owns:

```
llm.output_messages.0.message.reasoning       # the raw trace, verbatim
```

C3.1's second candidate — chosen so that the runner's own emission and any future
instrumentation that fixes this upstream converge on one name rather than two.

**Everything we compute rather than observe goes under `rlens.*`**, never into `llm.*`
or `openinference.*`: the locally-counted reasoning split (`rlens.token_count.reasoning`,
which is ours because S2 row 8 found no standard name for it), the pin tuple, the
`budget_bound` flag, `trace_quality`. Those two namespaces should keep meaning "what a
standard instrumentation would emit" — blending our metadata into them would make our
trees quietly non-comparable with the third-party fixture, and that comparability is the
whole of the B12 evidence.

Three properties this must hold, because they are the difference between an emission and a
workaround:

- **The runner writes it from the provider response it already holds** — the raw
  `reasoning` field S1 measured. No re-request, no reconstruction, no second call.
- **The analyzer does not know where it came from.** It reads an attribute off a span. A
  tree from our runner and a tree from a third party differ in whether the attribute is
  populated, never in how it is read.
- **Absence stays a first-class state.** A tree without it — every third-party tree today —
  sets `trace_quality: "partial"` with `reasoning` in `missing[]`, per C3.1's degradation
  rule. It does not error, and it does not silently produce an empty-step trace.

### 3. The third-party fixture is kept without reasoning text.

`langgraph_react_reference.json` stays exactly as captured, reasoning absent. It is the
subject of `test_third_party_spans.py`, which C7.1 names as B12's "integration, not a
rewrite" evidence — and that evidence is worth having *only* if the fixture keeps
documenting what a foreign agent actually emits. The runner's richer emission gets its own
fixture, owned by M1-6.

**This means the shipped system's headline capability is not exercised by the third-party
fixture, and that is the honest position:** we can ingest a stock LangGraph trace, and on a
stock LangGraph trace we can segment tool calls and answers but not native reasoning,
because the framework drops it. Stating that is worth more than a fixture doctored to imply
otherwise.

## Alternatives rejected

| Option | Why not |
| --- | --- |
| **Analyzer calls the provider for the missing trace** | Breaks I1 outright. The analyzer would need a provider client, a key and a network path, and would stop being reproducible from a committed span tree. This is the one option that is not on the table. |
| **Patch `ChatOpenAI` to carry `reasoning` through** | A monkeypatch on a third-party class, in the path of every arm, silently invalidated by any LangChain upgrade. It also makes the fixture no longer third-party — the agent would be adapted to us, which is precisely what M1-2 forbids. |
| **Upstream a fix to `langchain-openai`** | Right thing, wrong timescale. A PR does not land inside a 3-month PoC. Worth filing as a follow-up; not a plan dependency. |
| **Attach reasoning out-of-band (sidecar file keyed by span id)** | Two artifacts that can disagree, a join to get wrong, and the `ReasoningReport` stops being reproducible from one committed tree. |
| **Drop arms 1–2 to tool-call segmentation only** | Deletes the thing being studied. Arm 2 exists to show native thinking. |

## Consequences

- **M1-6 grows by ~0.5 h** — the emission and its unit test. The ingest half is *cheaper*
  than estimated (five precedence chains collapse to one candidate each, two branches
  deleted), so M1-6 holds at 2.5 h for ingest plus 0.5 h for emission. **W3 does not
  compress.** Recorded in the ledger this week, per breakdown §4.3.
- **`trace_quality: "partial"` becomes a real, reachable state in Month 1**, not a
  theoretical one — the third-party fixture exercises it from W2. That is a better position
  than discovering the degradation path at G1.
- **The spike deps are pinned and quarantined** in `spikes/requirements-s2.txt`, never in
  `analyzer/pyproject.toml`. An analyzer that imported LangGraph could not claim to ingest
  from it as a third party.
- **The instrumentor version is now load-bearing.** If `openinference-instrumentation-langchain`
  starts emitting reasoning, or renames anything, the fix is to re-run `make spike-s2` and
  amend this ADR against a fresh capture — not to add speculative fallbacks now.
