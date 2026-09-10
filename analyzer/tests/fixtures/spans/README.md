# Span-tree fixtures

`langgraph_react_reference.json` — **not a convenience fixture.** It is the subject of
`test_third_party_spans.py`, which C7.1 names as **B12's "integration, not a rewrite"
evidence**. Captured from a **stock LangGraph agent the analyzer has never seen**, and
never adapted to the analyzer. Owner: M1-2 (S2, W2).

**Captured 10 Sep 2026** by `make spike-s2` — 15 spans, one trace, a two-turn ReAct loop
around one TOOL span. Findings: [`docs/spikes/S2-otel.md`](../../../../docs/spikes/S2-otel.md).
Decision: [`ADR-002`](../../../../docs/decisions/ADR-002-span-emission.md).

**Do not edit it to make a test pass.** If an ingest change needs the fixture changed,
that is the finding. Re-capture with `make spike-s2` — which re-runs the whole delta — and
amend ADR-002 against the new capture.

**It carries no reasoning text, deliberately.** LangChain drops the runtime's `reasoning`
field before the instrumentor sees it (S2's control proves the runtime does send it), so
this is what a third-party tree honestly looks like. The runner's own richer emission
(ADR-002 §2) belongs in a separate fixture owned by M1-6 — keeping them apart is what stops
the integration claim from quietly becoming a claim about our own emitter.
