"""OTEL / OpenInference span tree -> NormalizedTrace (C3.1, C3.2).

Owner: M1-6, informed by the S2 attribute delta (M1-2). This module is a skeleton
placed by M1-0; the real mapping is written against the attribute names S2 observes
from a stock LangGraph agent, not against C3.1's aspirational table.

S2 has now run (`docs/spikes/S2-otel.md`), and it moved the target:

  * The live namespace is OpenInference `llm.*` / `openinference.*`. **No `gen_ai.*`
    attribute arrives at all** -- five of C3.1's nine rows list one, and all five are
    dead. ADR-002 deletes them rather than keeping them as fallbacks.
  * **Reasoning text does not reach the span tree.** LangChain drops the runtime's
    `reasoning` field before the instrumentor sees it. The fix is emission-side: the
    runner writes `llm.output_messages.0.message.reasoning` itself. A tree without it --
    every third-party tree -- degrades to `trace_quality: "partial"`, it does not error.
  * Tool-call arguments are on the **calling LLM span**, not the TOOL span, and tool
    results arrive as `output.value`; the capture has **zero span events**.

The mapping to write is tabulated in ADR-002 §1. Do not re-derive it from C3.1.
"""

from __future__ import annotations
