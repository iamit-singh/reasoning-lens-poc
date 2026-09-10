# S2 — OTEL / OpenInference attribute shape

| | |
| --- | --- |
| **Task** | M1-2 · W2 · 1.5 h |
| **Status** | **Run 10 Sep 2026 — complete.** 6 rows confirmed, 2 corrected, **1 absent** |
| **Decision doc** | [`../decisions/ADR-002-span-emission.md`](../decisions/ADR-002-span-emission.md) |
| **Harness** | `spikes/s2_otel_shape.py` · `make spike-s2` |
| **Fixture** | `analyzer/tests/fixtures/spans/langgraph_react_reference.json` |

## The question, precisely

Which attribute names **actually arrive** from a stock LangGraph agent — so C3.1's
mapping table is real rather than aspirational.

## Method

An unmodified `langgraph.prebuilt.create_react_agent` with one tool, under the stock
OpenInference LangChain instrumentor, exporting to an in-memory OTEL exporter. Generation
is the pinned local model (ADR-001). The agent is **never adapted to the analyzer** — that
is what makes the captured fixture B12's "integration, not a rewrite" evidence (C7.1)
rather than a convenience file.

Captured with:

| Package | Version |
| --- | --- |
| `langgraph` | 1.2.11 |
| `langchain-core` / `langchain-openai` | 1.6.2 |
| `openinference-instrumentation-langchain` | 0.1.76 |
| `opentelemetry-sdk` | 1.44.0 |

Pinned in `spikes/requirements-s2.txt`, which is **deliberately not** an analyzer
dependency: an analyzer that imported LangGraph could not claim to ingest from it as a
third party.

**Trace shape:** 15 spans, two LLM turns around one TOOL span, probe answered correctly
(7 × 43.5 = 304.5).

> **One harness defect worth recording, because it nearly became a false finding.** The
> first probe did not state the SKU, so the model asked a clarifying question instead of
> calling the tool, no TOOL span existed, and the delta reported the tool rows as *absent*.
> They were never *exercised*. S6 had already shown this model calls tools 20/20, so the
> contradiction was visible — but only because a previous spike had measured it. **An
> unexercised path reads exactly like a missing one.**

## The delta

| # | C3.1 row | Claimed attributes (precedence order) | Verdict | Actually observed | Action |
| --- | --- | --- | --- | --- | --- |
| 1 | Span kind | `openinference.span.kind` → `gen_ai.operation.name` | **CONFIRMED** | `openinference.span.kind` — values `CHAIN`, `LLM`, `TOOL`, `AGENT` | Keep the first candidate. **Drop the `gen_ai` fallback.** |
| 2 | Model id | `gen_ai.request.model`, `gen_ai.response.model` | **CORRECTED** | `llm.model_name`, `llm.provider`, `llm.system` | Read `llm.model_name`. Note it returns `gpt-oss:20b` — **the model *id*, not the pin tuple.** |
| 3 | **Thinking / reasoning text** | `gen_ai.completion.reasoning` → `llm.output_messages.*.message.reasoning` → provider block of type `thinking` | **ABSENT** | **nothing — under any name** | **Emission-side fix in M1-6. See ADR-002.** |
| 4 | Answer text | `gen_ai.completion.*.content` → `llm.output_messages.*.message.content` | **CONFIRMED** | `llm.output_messages.0.message.content` | Use the second candidate; the first never arrives. |
| 5 | Prompt text | `gen_ai.prompt.*.content` → `llm.input_messages.*` | **CONFIRMED** | `llm.input_messages.{n}.message.{content,role,name,tool_call_id}` | Use the second candidate. The indexed form carries the full turn history. |
| 6 | Tool call | `gen_ai.tool.name`, `tool.name`, `tool.parameters` | **CONFIRMED (partial)** | `tool.name`, `tool.description` on the TOOL span; **arguments on the *LLM* span** as `llm.output_messages.*.message.tool_calls.*.tool_call.{id,function.name,function.arguments}` | `tool.name` holds. **`tool.parameters` does not exist** — arguments live on the calling LLM span, not the TOOL span. |
| 7 | Tool result | span events / `output.value` on TOOL spans | **CONFIRMED (partial)** | `output.value` on the TOOL span | **There are zero span events in the entire tree.** Delete the span-events branch. |
| 8 | Tokens | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.reasoning_tokens` | **CORRECTED** | `llm.token_count.prompt`, `.completion`, `.total`, `.prompt_details.cache_read` | Rename all three. **No `reasoning_tokens` under any name** — see below. |
| 9 | Timing | span `startTime` / `endTime` | **CONFIRMED** | span `startTime` / `endTime` (ns since epoch) | No change. |

### The finding behind rows 1, 2, 4, 5, 8 — one mistake, made five times

**Not a single `gen_ai.*` attribute arrives. Zero, across all 15 spans.** C3.1 was written
against the OTEL GenAI semantic conventions; the stock instrumentation is **OpenInference**,
which emits its own `llm.*` / `openinference.*` namespace and does not dual-write.

This is why C3.1's precedence chains read as confirmed even where they are half wrong: every
chain that survives does so on its **non-`gen_ai`** candidate. Written as code unchecked,
`ingest/otel.py` would have carried a `gen_ai.*` branch in five places that could never fire.

## Row 3 — reasoning text does not reach the span tree, and it is not the runtime's fault

This is the row the architecture turns on, and "absent" understates it. The trace is not
summarised, not truncated, not buried in a serialised blob. **It is not there at all.**

The harness searched every attribute name in the tree for `reasoning`, `thinking`,
`thought`, `analysis`, `cot`, `scratchpad`; then searched every string *value* for a
serialised `"reasoning"` key or a `<think>` tag. Both came back empty. The LLM span's
`output.value` holds the full serialised `AIMessage`, and its `additional_kwargs` is
`{"refusal": null}`.

**The control names the culprit.** Three things could drop the trace — the runtime, the
LangChain adapter, or the instrumentor — and they need three different fixes, so the spike
issues the *same request* directly over HTTP with no LangChain in the path:

| Path | `reasoning` present? |
| --- | --- |
| Direct HTTP to the runtime, identical messages and tools | **yes — 173 chars** |
| Through `langchain_openai.ChatOpenAI` → instrumentor → span | **no** |

So: the runtime returns it (as S1 found, in a `reasoning` field on the message), and
`ChatOpenAI` does not map that non-standard field onto `AIMessage`. It is discarded before
the instrumentor ever sees it. **The instrumentor is faithful; it is serialising a message
that no longer contains the trace.**

> **Why this is an I1 question and not a parsing chore.** I1 says the analyzer's only input
> is a span tree. If the reasoning text is absent from the span tree, then either the
> analyzer reaches outside its input — which is the one thing I1 forbids — or the tree it
> receives has to contain the text. M1-2's own "On failure" clause pre-decided this: the
> fix is **emission-side, in M1-6**, and it is recorded in **ADR-002** rather than made as
> a silent code change.

### `reasoning_tokens` is absent too, and it is already solved

Row 8 finds no reasoning-token count under any name — consistent with S1, where the runtime
reported `completion_tokens` bundling reasoning with the answer and no split. **G0 check 2
already closed this**: the split is counted locally with `o200k_harmony`, and
`LOCAL_TOKENIZER` is part of the pin. Nothing new is owed here; row 8 is a rename, not a gap.

## Impact on M1-6 — stated now, per §4.3, not left as a W4 surprise

§4.3 asked for the estimate impact to be recorded the same week. It is **+0.5 h**, and the
composition matters more than the number:

| Change | Direction |
| --- | --- |
| Five `gen_ai.*` branches deleted before they were written | **cheaper** — the precedence chains collapse to one candidate each |
| Span-events branch for tool results deleted | **cheaper** |
| `tool.parameters` → read arguments off the calling LLM span instead | neutral |
| **Runner emits reasoning as a span attribute (ADR-002)** | **+0.5 h** — new work C10.2 does not budget |

M1-6 stays on its 2.5 h estimate for the ingest half; the emission work is the increment.
**W3 does not compress.** Had S2 run after M1-6 rather than before it, the same finding
would have arrived as a rewrite of code already written against a namespace that does not
exist — which is the entire argument for §4.1's ordering.

## What the fixture is for

`analyzer/tests/fixtures/spans/langgraph_react_reference.json` — 15 spans, captured from an
agent the analyzer has never seen. It is the subject of `test_third_party_spans.py` (C7.1,
B12). It is **kept as captured**: if a future ingest change needs the fixture edited to
pass, that is the finding, and the fixture is not what should change.

Note that the fixture as captured **has no reasoning text**, and that is deliberate. It
documents what a *third-party* agent emits. The runner's own richer emission (ADR-002) is a
separate fixture, owned by M1-6 — keeping the two apart is what stops the integration claim
from quietly becoming a claim about our own emitter.
