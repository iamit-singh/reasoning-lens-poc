"""Provider abstraction and MOCK_LLM cassette replay.

The ONLY place in the analyzer where provider payload shapes may appear (C2.2), together
with ``ingest/otel.py``. C13.2 credits "S1, then the abstraction layer in M1-6" with
retiring the provider-hides-thinking risk -- **that credit only holds if this really is
the sole place a provider's response shape is known**, which is why ``check_provider_symbols.sh``
greps the other modules for it rather than trusting the convention.

Owner: M1-6.

Two notes on what is deliberately *not* here
--------------------------------------------
* **No provider SDK.** The local runtime and OpenAI both speak the OpenAI wire format
  (ADR-001), and what we need of it is one POST. ``urllib`` keeps the analyzer installable
  without the ``[providers]`` extra and keeps the shape visible in this file rather than
  behind a client object. The extra stays declared for the analysis tier.
* **No analysis calls.** This module generates. Classification and judging get their own
  entry points; mixing them here would make the C2.2 grep a weaker guarantee.
"""

from __future__ import annotations

import json
import os
import pathlib
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from rlens.versions import GenerationPin

#: Which tiktoken encoding belongs to which local model. A lookup, never a default:
#: gpt-oss uses harmony, the approved fallback qwen3 does not, and counting one model's
#: text with another's encoding yields a plausible WRONG number -- the worst kind, because
#: nothing looks broken. An unknown model reports no count, which is honest. Mirrors S1.
TOKENIZERS: dict[str, str] = {"gpt-oss": "o200k_harmony"}

CASSETTE_DIR = pathlib.Path(__file__).parent.parent.parent / "tests/fixtures/cassettes"


class ProviderError(RuntimeError):
    """The provider failed after its one retry. The arm is marked failed; others render."""


@dataclass(frozen=True)
class Completion:
    """One model call's result, normalised. **No provider key names survive past here.**"""

    text: str
    #: Raw, unsummarised reasoning. Empty string when the arm ran with thinking off --
    #: which is a real state (arm 1), not a missing value, and is why this is not None.
    reasoning: str
    model: str
    finish_reason: str

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    #: Counted locally with the model's own encoding, because the runtime reports
    #: `completion_tokens` bundling reasoning WITH the answer and no split (S1, G0 check 2).
    #: None when the encoding for this model is unknown.
    reasoning_tokens: int | None
    answer_tokens: int | None
    tokenizer: str | None
    #: billed completion_tokens - (reasoning + answer). The harmony format wraps each
    #: channel in structural tokens that are billed and are not in the extracted text, so
    #: a small positive residual is expected. Large or negative means the wrong encoding.
    structural_token_residual: int | None

    #: True when the thinking budget bound. See `_budget_bound` -- locally this is a
    #: MEASUREMENT, not a cap, and the difference is recorded rather than smoothed over.
    budget_bound: bool
    #: The effort actually SENT. Recorded because the request is the only half we
    #: control: S7 found `none` and `think: false` are silently ignored, so what was
    #: asked for and what happened are separate facts and both belong in the trace.
    requested_effort: str
    attempts: int
    replayed: bool = False
    invocation_parameters: dict[str, Any] = field(default_factory=dict)


def _encoding_for(model: str) -> str | None:
    """The encoding for this model, or None if we do not know it.

    ``LOCAL_TOKENIZER`` overrides, because it is part of the pin (ADR-001): swapping the
    model without swapping the tokenizer is exactly the mistake this refuses to make
    quietly.
    """
    override = os.environ.get("LOCAL_TOKENIZER")
    if override:
        return override
    for prefix, enc in TOKENIZERS.items():
        if model.startswith(prefix):
            return enc
    return None


def _count_split(
    model: str, reasoning: str, answer: str
) -> tuple[int | None, int | None, str | None]:
    enc_name = _encoding_for(model)
    if not enc_name:
        return None, None, None
    try:
        import tiktoken

        enc = tiktoken.get_encoding(enc_name)
    except Exception:
        # An unavailable encoding must not fail a run, but it must not silently produce
        # a number either. No count is a reportable state; a guessed count is not.
        return None, None, f"{enc_name} (unavailable)"
    return len(enc.encode(reasoning)), len(enc.encode(answer)), enc_name


def _budget_bound(finish_reason: str, reasoning_tokens: int | None, budget: int) -> bool:
    """Did the thinking budget bind?

    **The plan assumed a provider-enforced budget; locally there is none.** ollama exposes
    `reasoning_effort`, not a token cap, so nothing server-side stops the model thinking.
    The flag therefore changes meaning: it is a *measurement* that the trace reached the
    budget C4.1 nominated, not evidence that the provider truncated it.

    That is the more useful of the two, and it must not be quietly dropped just because
    the mechanism it named does not exist here: B4 #7 measures cost-of-thought, and a
    silently capped trace caps the metric. `finish_reason == "length"` is the genuine
    truncation signal and is kept separate from reaching the nominal budget.
    """
    if finish_reason == "length":
        return True
    return reasoning_tokens is not None and budget > 0 and reasoning_tokens >= budget


# ------------------------------------------------------------------ cassettes (MOCK_LLM)
def _cassette_path(name: str) -> pathlib.Path:
    return CASSETTE_DIR / f"{name}.json"


def _replay(name: str) -> Completion:
    """Replay a recorded response. The CI default -- MOCK_LLM=1 in every PR job.

    Recording the full bank x arms matrix is M1-14 (W4). What lives here is the replay
    half plus the handful of cassettes the span-contract test needs, because a DoD of
    "spans pass test_span_contract.py" cannot be met by a test that needs a GPU.
    """
    path = _cassette_path(name)
    if not path.exists():
        raise ProviderError(
            f"MOCK_LLM=1 but no cassette at {path}. Record one with "
            f"`make record-cassettes` (M1-14), or run with MOCK_LLM=0 against a served model."
        )
    data = json.loads(path.read_text())
    return Completion(**{**data, "replayed": True})


def record_cassette(name: str, completion: Completion) -> pathlib.Path:
    """Write a completion to a cassette. Used by M1-14's recorder and by the S-spikes."""
    from dataclasses import asdict

    path = _cassette_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in asdict(completion).items() if k != "replayed"}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


# ------------------------------------------------------------------ the call
def _post(url: str, payload: dict[str, Any], api_key: str, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result: dict[str, Any] = json.load(resp)
        return result


def generate(
    messages: list[dict[str, str]],
    *,
    pin: GenerationPin,
    thinking: bool,
    reasoning_effort: str | None = None,
    cassette: str | None = None,
    timeout: int | None = None,
    base_url: str | None = None,
) -> Completion:
    """One model call against the pinned local generation model.

    `thinking` selects the arm's regime, and the two arms differ in more than a flag --
    see `rlens.runner.arms`, which owns the prompts. Retries once with jitter on a
    transport error, per C4.1; a second failure raises `ProviderError` and the caller
    marks that arm failed while the other arms still render.
    """
    if os.environ.get("MOCK_LLM") == "1":
        if not cassette:
            raise ProviderError("MOCK_LLM=1 requires a cassette name")
        return _replay(cassette)

    url = (base_url or os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
    url += "/chat/completions"
    api_key = os.environ.get("LOCAL_API_KEY", "ollama")
    timeout = timeout if timeout is not None else int(os.environ.get("ARM_TIMEOUT_S", "180"))
    budget = int(os.environ.get("THINKING_BUDGET_TOKENS", "8000"))

    payload: dict[str, Any] = {
        "model": pin.model,
        "messages": messages,
        "temperature": pin.temperature,
        "top_p": pin.top_p,
        "seed": pin.seed,
    }
    # BOTH arms name an effort, and arm 1's is `low` rather than absent. Omitting the
    # parameter yields the runtime's DEFAULT, which sits close to arm 2's -- the arms
    # would then differ only in their system prompt while thinking almost identically,
    # and the cost-of-thought baseline would be measuring nothing. ADR-004.
    effort = reasoning_effort or (pin.reasoning_effort if thinking else None)
    if effort:
        payload["reasoning_effort"] = effort

    last: Exception | None = None
    for attempt in (1, 2):
        try:
            data = _post(url, payload, api_key, timeout)
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt == 2:
                raise ProviderError(f"{pin.model}: {type(exc).__name__}: {exc}") from last
            time.sleep(0.5 + random.random())  # jitter, not cryptography
    else:  # pragma: no cover -- the loop always breaks or raises
        raise ProviderError("unreachable")

    choice = data["choices"][0]
    msg = choice["message"]
    text = msg.get("content") or ""
    # S1: the local runtime returns the raw trace in a `reasoning` field on the message,
    # not as inline <think> tags. Inline tags are the fallback for other models -- and are
    # a materially worse contract, since a delimiter can be emitted mid-sentence.
    reasoning = msg.get("reasoning") or ""
    if not reasoning and "<think>" in text:
        head, _, tail = text.partition("</think>")
        reasoning, text = head.replace("<think>", "").strip(), tail.strip()

    usage = data.get("usage") or {}
    completion_tokens = int(usage.get("completion_tokens") or 0)
    r_tok, a_tok, enc = _count_split(pin.model, reasoning, text)
    residual = None
    if r_tok is not None and a_tok is not None and completion_tokens:
        residual = completion_tokens - (r_tok + a_tok)
    finish = choice.get("finish_reason") or ""

    return Completion(
        text=text,
        reasoning=reasoning,
        model=data.get("model") or pin.model,
        finish_reason=finish,
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=completion_tokens,
        total_tokens=int(usage.get("total_tokens") or 0),
        reasoning_tokens=r_tok,
        answer_tokens=a_tok,
        tokenizer=enc,
        structural_token_residual=residual,
        budget_bound=_budget_bound(finish, r_tok, budget if thinking else 0),
        requested_effort=effort or "",
        attempts=attempt,
        invocation_parameters={k: v for k, v in payload.items() if k not in ("messages",)},
    )
