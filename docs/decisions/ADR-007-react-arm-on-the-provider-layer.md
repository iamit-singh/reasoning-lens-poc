# ADR-007 — Arm 3 is a ReAct loop on our own provider layer, not LangGraph

| | |
| --- | --- |
| **Status** | **Accepted** — 11 Sep 2026 (W3) |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | C4.1's arm-3 row ("LangGraph ReAct loop, `max_turns = 6`") — the loop, the turn cap and the tools are unchanged; only the implementation substrate is |
| **Evidence** | the probe below · [ADR-002](ADR-002-span-emission.md) · `docs/spikes/S2-otel.md` · `analyzer/tests/test_third_party_spans.py` |
| **Depends on** | [ADR-002](ADR-002-span-emission.md) — same finding, second consequence |

## Context

C4.1 specifies arm 3 as a *"LangGraph ReAct loop"*. Before building it, one thing needed
checking: **where does the thought text live on a tool-calling turn?** The answer decides
whether LangGraph is usable at all, because S2 already established that
`langchain_openai.ChatOpenAI` drops the runtime's `reasoning` field before any
instrumentation sees it — that finding is what ADR-002 exists to work around for arms 1
and 2.

One request to the served model, two tools offered, a question requiring a lookup:

| Field on the returned message | Length | Content |
| --- | --- | --- |
| `content` | **0 chars** | `''` |
| `reasoning` | 86 chars | `'We need to look up the population of Fairhaven. Use lookup tool. Then subtract 12,400.'` |
| `tool_calls` | 1 | `lookup{"query": "population of Fairhaven"}` |

**On a tool-calling turn the visible content is empty and the entire thought is in
`reasoning`** — the one field LangChain discards.

C4.2 defines ReAct segmentation as *"each `TOOL` span → one `tool_call` step + one
`observation` step; **the thought text preceding it** → one `thought` step"*. Put together:

> A LangGraph arm 3 would emit a structurally perfect ReAct trace containing **no thought
> text whatsoever**. Every `thought` step would be empty. The arm whose traces are the
> most interesting thing in the product — an agent visibly deciding which tool to reach
> for — would arrive with its reasoning panel blank, and nothing would look broken.

## Decision

**Implement the ReAct loop directly on `rlens.llm`** (`rlens/runner/react.py`), with
`max_turns = 6`, `calculator` and `lookup` exactly as C4.1 specifies, emitting through the
same `emit.py` as arms 1 and 2.

Three things make this an implementation choice rather than a scope reduction:

1. **The loop is not the hard part.** ReAct is: ask, run the tools it asked for, feed the
   observations back, stop when it answers without calling one. That is ~60 lines. What
   LangGraph would contribute is graph machinery this arm has no use for — there is one
   node and one edge — at the cost of the reasoning text.
2. **B12's evidence does not run through this arm.** C2.2's third requirement is that *the
   analyzer* must work against a span tree from a **stock LangGraph agent it has never
   seen**, and that is `test_third_party_spans.py` against the capture S2 committed. It is
   green, it stays green, and it is unaffected by how arm 3 is built. B12's claim is
   "integration, not a rewrite" — an assertion about the analyzer's input contract, not
   about our runner's dependencies.
3. **The span names are theirs, not ours.** Arm 3's TOOL spans carry `tool.name`,
   `tool.description`, `input.value`, `output.value`, `output.mime_type` — read directly
   off the stock LangGraph capture rather than invented. So C4.2's segmenter gets **one**
   ReAct code path that serves our arm 3 and a third-party agent equally. Had we emitted a
   private dialect, this decision would have cost the analyzer a second branch, and that
   is the form "integration, not a rewrite" actually takes in the code.

## What this also avoids

- **A second provider integration.** `llm.py` is meant to be the sole place a provider
  payload shape appears (C2.2 rule 2, grep-enforced). Routing one arm through
  `langchain_openai` would have put a second one in the tree — and C13.2's credit to "the
  abstraction layer in M1-6" for retiring the provider risk only holds while that is true.
- **Two dependency weights.** `spikes/requirements-s2.txt` is explicit that langgraph and
  langchain-openai are *spike-only deps, NOT analyzer deps*. I1 wants the analyzer
  installable without the machinery that produces traces; the `runner` extra carries the
  OTEL SDK and now needs nothing more.
- **A silent regression path.** If LangChain later stops dropping `reasoning`, nothing
  here has to change — and ADR-002's choice of C3.1's own attribute name means our trees
  and a fixed upstream converge rather than diverge.

## Consequences

- **Arm 3's cost is the whole loop.** `reasoning_tokens` on the final completion is the
  last turn only; the CLI and the metrics sum across turns. A 3-turn agent reported by its
  final turn understates its cost by most of it.
- **One cassette per turn** (`{item}.react.t0`, `.t1`, …). A single cassette per arm could
  only replay the first call, and the loop would then answer its own second turn with its
  first turn's response — a green test for a conversation that never happened.
- **One timeout for the arm, not per turn.** Per-turn timeouts would let a stuck agent
  spend `max_turns × ARM_TIMEOUT_S` — 18 minutes at the committed settings — while every
  individual turn looked healthy.
- **`max_turns` exhaustion is `trace_quality: "partial"`**, not a failure. An agent that
  cannot finish in six turns is an observation about the agent, and C4.1 wants the partial
  trace rather than nothing.
- **The `lookup` tool description enumerates the corpus keys**, and that is load-bearing
  under lever L2. The probe above shows the model asking for `"population of Fairhaven"` —
  a sensible phrasing that misses every time under exact match. L2 forbids fuzzy matching,
  so the only move left inside the lever is to make the contract discoverable. With the
  keys listed, the same model asked for `fairhaven_population` and `brightwater_population`
  verbatim and answered `mb-08` correctly in 3 turns. **This does not scale past a few
  dozen facts and does not have to: L2 fixes the corpus at 12.** If it grows, the
  description stops being the right mechanism, and that is a decision to record rather than
  a limit to paper over.
