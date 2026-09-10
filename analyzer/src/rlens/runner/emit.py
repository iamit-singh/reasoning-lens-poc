"""OTEL span emission for the strategy arms. C4.1, and **ADR-002 is the reason this exists**.

S2 established that a stock LangGraph trace does not carry reasoning text at all --
`langchain_openai.ChatOpenAI` drops the runtime's `reasoning` field before the
instrumentor sees it. I1 says the analyzer's only input is a span tree, so either the
analyzer reaches outside its input (forbidden) or the tree contains the text. ADR-002
chose the second: **the runner emits it.**

Three properties that make this an emission and not a workaround, all load-bearing:

* The value written is the raw `reasoning` the provider already returned. No re-request,
  no reconstruction.
* It is written under C3.1's own second candidate name,
  `llm.output_messages.0.message.reasoning`, so that our trees and any future
  instrumentation that fixes this upstream converge on ONE name rather than two.
* **The analyzer never learns where a tree came from.** It reads an attribute. A
  third-party tree simply has it empty, and degrades to `trace_quality: "partial"`.

Owner: M1-6.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from rlens.versions import RUNNER_VERSION, GenerationPin

if TYPE_CHECKING:
    from rlens.llm import Completion

#: Our own attributes live under `rlens.*`, never mixed into `llm.*`/`openinference.*`.
#: Anything in those namespaces should mean "what a standard instrumentation would emit";
#: blending our metadata into them would make our trees quietly non-comparable with the
#: third-party fixture, which is the one thing the B12 evidence rests on.
NS = "rlens"


class SpanEmissionError(RuntimeError):
    pass


def _require_otel() -> Any:
    try:
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError as exc:  # pragma: no cover
        raise SpanEmissionError(
            "The runner needs the OTEL SDK: pip install -e 'analyzer[runner]'. "
            "It is an extra, not a core dependency -- the analyzer INGESTS span trees "
            "and must stay installable without the machinery that produces them."
        ) from exc
    return TracerProvider


def llm_span_attributes(
    comp: Completion,
    messages: list[dict[str, str]],
    pin: GenerationPin,
) -> dict[str, Any]:
    """The LLM span's attributes, in the namespace S2 measured as live (ADR-002 §1).

    Deliberately no `gen_ai.*` key. S2 found not one of them arrives from real
    instrumentation, and ADR-002 deleted those branches rather than demoting them --
    emitting names nothing else emits would put the divergence back on our side.
    """
    attrs: dict[str, Any] = {
        "openinference.span.kind": "LLM",
        "llm.model_name": comp.model,
        "llm.provider": "local",
        "llm.system": pin.runtime,
        "llm.finish_reason": comp.finish_reason,
        "llm.invocation_parameters": json.dumps(comp.invocation_parameters, sort_keys=True),
        "llm.token_count.prompt": comp.prompt_tokens,
        "llm.token_count.completion": comp.completion_tokens,
        "llm.token_count.total": comp.total_tokens,
    }
    for i, m in enumerate(messages):
        attrs[f"llm.input_messages.{i}.message.role"] = m["role"]
        attrs[f"llm.input_messages.{i}.message.content"] = m["content"]
    attrs["llm.output_messages.0.message.role"] = "assistant"
    attrs["llm.output_messages.0.message.content"] = comp.text

    # ADR-002 §2. Only set when non-empty: an empty string here would be indistinguishable
    # from "the model thought and produced nothing", and arm 1 legitimately has no trace.
    # Absence is the honest encoding of absence.
    if comp.reasoning:
        attrs["llm.output_messages.0.message.reasoning"] = comp.reasoning

    # No reasoning-token count exists in either namespace (S2 row 8), and the runtime
    # reports none (S1). This is ours, counted locally with the pinned encoding, and it
    # is named in our own namespace precisely BECAUSE it is not a standard attribute --
    # putting it under `llm.token_count.*` would imply an instrumentation emitted it.
    if comp.reasoning_tokens is not None:
        attrs[f"{NS}.token_count.reasoning"] = comp.reasoning_tokens
        attrs[f"{NS}.token_count.answer"] = comp.answer_tokens
        attrs[f"{NS}.tokenizer"] = comp.tokenizer
        if comp.structural_token_residual is not None:
            attrs[f"{NS}.token_count.structural_residual"] = comp.structural_token_residual

    attrs[f"{NS}.budget_bound"] = comp.budget_bound
    attrs[f"{NS}.requested_effort"] = comp.requested_effort
    attrs[f"{NS}.attempts"] = comp.attempts
    attrs[f"{NS}.replayed"] = comp.replayed
    return attrs


def arm_span_attributes(
    strategy: str,
    item_id: str,
    pin: GenerationPin,
    *,
    deterministic: bool,
    trace_quality: str,
    failed_reason: str | None = None,
) -> dict[str, Any]:
    """The root CHAIN span's attributes: one per arm, per C4.1."""
    attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        f"{NS}.strategy": strategy,
        f"{NS}.item_id": item_id,
        f"{NS}.runner_version": RUNNER_VERSION,
        # The pin TUPLE, not just an id: ADR-001 is explicit that an id does not
        # reproduce a number. The fingerprint is what enters the cache key, and the
        # fields travel beside it so a reader can see what it is a fingerprint OF.
        f"{NS}.pin.fingerprint": pin.fingerprint(),
        f"{NS}.pin.model": pin.model,
        f"{NS}.pin.digest": pin.digest,
        f"{NS}.pin.quantization": pin.quantization,
        f"{NS}.pin.runtime": pin.runtime,
        f"{NS}.pin.temperature": pin.temperature,
        f"{NS}.pin.top_p": pin.top_p,
        f"{NS}.pin.seed": pin.seed,
        f"{NS}.pin.reasoning_effort": pin.reasoning_effort,
        f"{NS}.deterministic": deterministic,
        f"{NS}.trace_quality": trace_quality,
    }
    if failed_reason:
        attrs[f"{NS}.failed_reason"] = failed_reason
    return attrs


# ------------------------------------------------------------------ exporters
def build_tracer_provider(collector: Any) -> Any:
    """A TracerProvider writing to the in-process collector and, if configured, Langfuse.

    C4.1 requires both. The in-process collector is what the analyzer reads and what the
    span-contract test asserts on; Langfuse is the operator's view -- C8 reads cost
    dashboards from it and logs judge output there, which is what makes a wrong flag
    inspectable after the fact.
    """
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(collector))
    langfuse = _langfuse_exporter()
    if langfuse is not None:
        provider.add_span_processor(SimpleSpanProcessor(langfuse))
    return provider


def langfuse_status() -> str:
    """Whether the Langfuse leg is live -- reported by the CLI, never assumed.

    A telemetry sink that is silently absent is worse than one that is absent: the
    dashboards look empty and nobody knows whether that means "no runs" or "no export".
    """
    if os.environ.get("LANGFUSE_ENABLED", "1") != "1":
        return "disabled (LANGFUSE_ENABLED=0)"
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return "NOT CONFIGURED (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY unset)"
    return f"enabled -> {os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com')}"


def _langfuse_exporter() -> Any | None:
    """Langfuse over OTLP/HTTP (Appendix D #6: cloud free tier).

    Langfuse ingests OTLP directly, so this is one more span processor rather than a
    second instrumentation path -- the spans Langfuse receives are byte-for-byte the ones
    the analyzer reads. A separate SDK would let the two views drift, and then a number
    on a dashboard could disagree with a number in a report with no way to tell which
    is wrong.
    """
    if os.environ.get("LANGFUSE_ENABLED", "1") != "1":
        return None
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (public and secret):
        # Not an error. MOCK_LLM CI runs and offline development must work with no
        # telemetry account; the CLI prints the status so it is visible, not silent.
        return None

    import base64

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    token = base64.b64encode(f"{public}:{secret}".encode()).decode()
    return OTLPSpanExporter(
        endpoint=f"{host}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {token}"},
    )
