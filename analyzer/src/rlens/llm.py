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
* **Analysis calls live here too, and that reverses a note M1-6 left.** M1-6 wrote that
  classification would get its own entry point because "mixing them here would make the
  C2.2 grep a weaker guarantee". M1-9 found that backwards. The grep's guarantee comes
  from ``classify.py``/``judge.py``/``consistency.py`` being clean of provider shapes --
  and a *third* provider-aware module would weaken C2.2's claim, which is a single
  sentence naming exactly two files. So ``generate`` and ``analyze`` sit side by side,
  the sentence stays literally true, and the two are kept apart by being different
  functions rather than different modules.

  They share nothing but the file, deliberately: different tier, different provider,
  different pin, different failure rules. ``generate`` wants long raw reasoning;
  ``analyze`` wants short structured rows and as little reasoning as the model will
  accept (S3, ADR-001).
"""

from __future__ import annotations

import concurrent.futures
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

    #: Tool calls the model asked for, normalised to `{id, name, arguments}` with
    #: `arguments` already parsed from the JSON string the wire carries. Empty for arms 1
    #: and 2, which are given no tools -- an empty tuple, not None, because "asked for no
    #: tools" is a real and common outcome rather than a missing value.
    #:
    #: Defaulted so the cassettes recorded before arm 3 existed still replay. A required
    #: field here would have made every committed cassette unreadable, and re-recording
    #: them to add an empty list is exactly the kind of churn a default prevents.
    tool_calls: tuple[dict[str, Any], ...] = ()


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
    # JSON has no tuples, and a cassette recorded before arm 3 existed has no tool_calls
    # at all. Both are normalised here rather than at every call site.
    data["tool_calls"] = tuple(data.get("tool_calls") or ())
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
    tools: list[dict[str, Any]] | None = None,
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
    # Arm 3 only. Absent for arms 1 and 2, and absent is not the same as `[]`: an empty
    # tools array is a request that says "you may call tools" and offers none, which some
    # runtimes answer by refusing to answer at all.
    if tools:
        payload["tools"] = tools
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

    # The wire carries `arguments` as a JSON *string*. Parsing it here is the whole reason
    # this belongs in llm.py: it is a provider payload shape, and C2.2 confines those to
    # this module. A malformed string is kept as `{"_raw": ...}` rather than dropped --
    # S6 measured 20/20 well-formed calls, but it measured four short prompts, not a
    # six-turn loop with tool results fed back in, and S6's own write-up says so. A call
    # we could not parse must reach the loop as a visible bad call.
    tool_calls: list[dict[str, Any]] = []
    for raw in msg.get("tool_calls") or []:
        fn = raw.get("function") or {}
        argtext = fn.get("arguments") or "{}"
        try:
            parsed = json.loads(argtext)
            if not isinstance(parsed, dict):
                parsed = {"_raw": argtext}
        except json.JSONDecodeError:
            parsed = {"_raw": argtext}
        tool_calls.append(
            {"id": raw.get("id") or "", "name": fn.get("name") or "", "arguments": parsed}
        )

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
        invocation_parameters={k: v for k, v in payload.items() if k not in ("messages", "tools")},
        tool_calls=tuple(tool_calls),
    )


# ------------------------------------------------------- the analysis tier (C4.3, M1-9)
#: Backends the analysis tier can run on. Both are measured configurations, not a primary
#: and a hack: ADR-001 makes local-only a supported answer to "can this run on a laptop
#: with no API access?", and the calibration harness scores both against the same human
#: labels. Neither is allowed to be the silent default of the other.
ANALYSIS_BACKENDS = ("hybrid", "local")


class AnalysisTruncated(ProviderError):
    """The output cap bound: the response is cut off mid-JSON.

    **A hard error, deliberately not a parse failure.** S3 measured this as
    `finish_reason: length` at a content length of exactly 4,095 characters across three
    identical runs -- a cap, not a competence limit. The repair retry exists for a model
    that produced malformed JSON and can do better when told so; a truncated response will
    truncate again at the same place, so retrying it burns a call to reach the same
    outcome and then reports `classifier_parse_failure`, which names the wrong cause.

    The right response is to raise, loudly, naming the cap. See S3 consequence 1.
    """


@dataclass(frozen=True)
class AnalysisResult:
    """One analysis call's result. The mirror of `Completion` for the other tier.

    Much smaller than `Completion`, and the asymmetry is the point: for generation the
    reasoning text *is* the artifact and every token of it is measured. For analysis the
    reasoning is a cost to be minimised and the only thing that matters is whether the
    rows came back whole.
    """

    text: str
    model: str
    finish_reason: str
    backend: str
    prompt_tokens: int
    completion_tokens: int
    #: Billed reasoning tokens where the provider reports them. Unlike the generation
    #: tier, this is NOT counted locally and cannot be: the text is never returned (S1,
    #: 11 Sep -- 384 tokens billed, 0 chars back). None on backends that report nothing.
    reasoning_tokens: int | None
    attempts: int
    latency_ms: int
    replayed: bool = False


def _analysis_backend() -> str:
    backend = os.environ.get("ANALYZER_BACKEND", "hybrid").strip() or "hybrid"
    if backend not in ANALYSIS_BACKENDS:
        raise ProviderError(
            f"ANALYZER_BACKEND={backend!r} is not one of {ANALYSIS_BACKENDS}. "
            "A typo here would otherwise silently select the default and publish a number "
            "attributed to the wrong tier."
        )
    return backend


def request_digest(prompt: str, *, backend: str, model: str) -> str:
    """What an analysis cassette is keyed by (M1-14).

    The prompt bundle version is folded in by the caller through the prompt text itself --
    the prompt IS the rendered bundle -- so a bundle edit changes this digest, which is
    what "once per prompt-bundle version" means in practice.
    """
    import hashlib

    return hashlib.sha256(f"{backend}\x1f{model}\x1f{prompt}".encode()).hexdigest()[:16]


def _replay_analysis(name: str, expected_digest: str) -> AnalysisResult:
    path = _cassette_path(name)
    if not path.exists():
        raise ProviderError(
            f"MOCK_LLM=1 but no analysis cassette at {path}. Record one with "
            f"`make record-cassettes` (M1-14)."
        )
    data = json.loads(path.read_text())
    recorded = data.pop("request_digest", None)
    # **The check that makes a named cassette as strong as a hash-keyed one.** M1-14's spec
    # says cassettes are keyed by a hash of the request. Keying the FILENAME by a hash
    # would make the directory unreadable and would have orphaned the 49 generation
    # cassettes; recording the digest INSIDE and refusing a mismatch gives the same
    # guarantee -- you cannot replay a response recorded for a different request -- while
    # the filename still says which item and arm it belongs to.
    if recorded is not None and recorded != expected_digest:
        raise ProviderError(
            f"cassette {path.name} was recorded for a different request "
            f"({recorded} != {expected_digest}). The prompt bundle or the model changed; "
            f"re-record with `make record-cassettes`."
        )
    return AnalysisResult(**{**data, "replayed": True})


def record_analysis_cassette(
    name: str, result: AnalysisResult, *, request_digest: str
) -> pathlib.Path:
    """Write an analysis cassette. M1-14's recorder."""
    from dataclasses import asdict

    path = _cassette_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in asdict(result).items() if k != "replayed"}
    payload["request_digest"] = request_digest
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int
) -> dict[str, Any]:
    """A plain POST. **The deadline is NOT enforced here** -- see `_with_deadline`.

    It was, briefly, and a test showed why that was the wrong altitude: a budget wrapped
    around the HTTP helper bounds the transport and nothing else, so any other way a
    backend can block goes unbounded and the guarantee reads stronger than it is.
    """
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body: dict[str, Any] = json.load(resp)
        return body


def _with_deadline(fn: Any, timeout: int) -> Any:
    """Run `fn()` under a **wall-clock** budget and give up on it if it overruns.

    `urlopen(timeout=...)` bounds each socket *operation*, and that turned out not to bound
    the request. M1-9's first full pass measured a single-chunk call taking **969 seconds
    against a 110-second `ANALYSIS_DEADLINE_S`** -- so the deadline was decorative in the
    one place C11 budgets 18 seconds for.

    The budget is enforced from **outside** the call, because the block was inside it: a
    deadline checked between reads would never have run, there being no reads to check
    between. The worker is a daemon thread, so if the socket really is wedged it stays
    wedged and the caller is released on time. **Abandoning one socket is the cheaper
    failure** -- the alternative is a demo that hangs.

    **The generation tier is deliberately not wrapped.** `ARM_TIMEOUT_S` bounds arms whose
    legitimate traces run to minutes, so enforcing a hard budget there changes the
    behaviour of the thing under study, and it belongs with the task that owns C4.1's
    partial-trace path rather than being smuggled in beside a classifier fix.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(
                f"the call exceeded its {timeout}s budget. Raise ANALYSIS_DEADLINE_S if "
                f"this workload legitimately needs longer; C11 budgets 18s for it."
            ) from exc
    finally:
        # `wait=False` is the point: shutting down with wait=True would re-block for
        # exactly as long as the hang this exists to escape.
        pool.shutdown(wait=False, cancel_futures=True)


def _analyze_hosted(
    prompt: str, model: str, cap: int, effort: str, timeout: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ProviderError(
            "ANALYZER_BACKEND=hybrid but OPENAI_API_KEY is unset. Set it, or run the "
            "measured local-only configuration with ANALYZER_BACKEND=local (ADR-001)."
        )
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        # Asking for a JSON object is the cheap half of the contract; the schema check in
        # `classify.py` is the half that matters. JSON mode guarantees parseable, not
        # correct: it will happily return `{}`.
        "response_format": {"type": "json_object"},
        "max_completion_tokens": cap,
        "reasoning_effort": effort,
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        timeout,
    )
    choice = (data.get("choices") or [{}])[0]
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "text": (choice.get("message") or {}).get("content") or "",
        "model": data.get("model") or model,
        "finish_reason": choice.get("finish_reason") or "",
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "reasoning_tokens": details.get("reasoning_tokens"),
    }, payload


def _analyze_local(
    prompt: str, model: str, cap: int, effort: str, timeout: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The local analyzer tier, on the **native** endpoint.

    Not the OpenAI-compatible one. S3 measured `max_tokens` there being accepted and
    silently ignored -- 16,000 still returned `finish_reason: length` at ~1,854 tokens,
    three runs byte-identical. `options.num_predict` is the only cap this runtime honours,
    and it is only available here.
    """
    base = (os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
    url = base.removesuffix("/v1") + "/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "think": effort,
        "options": {
            "temperature": 0,
            "top_p": 1.0,
            "seed": int(os.environ.get("GEN_SEED", "0")),
            "num_predict": cap,
            "num_ctx": int(os.environ.get("ANALYZE_NUM_CTX", "16384")),
        },
    }
    data = _post_json(url, payload, {"Content-Type": "application/json"}, timeout)
    # `done_reason` is this runtime's `finish_reason`; normalising it here is exactly the
    # kind of provider-shape knowledge C2.2 confines to this file.
    done = data.get("done_reason") or ""
    return {
        "text": (data.get("message") or {}).get("content") or "",
        "model": data.get("model") or model,
        "finish_reason": "length" if done == "length" else done,
        "prompt_tokens": int(data.get("prompt_eval_count") or 0),
        "completion_tokens": int(data.get("eval_count") or 0),
        "reasoning_tokens": None,
    }, payload


def analyze(
    prompt: str,
    *,
    cassette: str | None = None,
    timeout: int | None = None,
    cap: int | None = None,
    tier: str = "triage",
) -> AnalysisResult:
    """One analysis call. Classification, triage, consistency and escalation all use it.

    Three things S3 paid for, enforced here rather than remembered by each caller:

    1. **The output cap is explicit**, and set through the parameter the backend actually
       honours -- which differs between them, and where the local runtime accepts and
       ignores the obvious one.
    2. **Reasoning effort is low.** An analysis call at default effort spent its entire
       output budget in the reasoning channel and returned empty content while billing
       2,293 tokens. Classification is a labelling task.
    3. **A bound cap raises.** See `AnalysisTruncated`.

    Retries once on a transport error, matching `generate`. It does **not** retry a
    truncation or a bad-JSON response: the first is hopeless and the second is the
    caller's repair retry to spend, once, with the validation error attached (C4.3).
    """
    if tier not in ("triage", "escalate"):
        raise ProviderError(f"tier must be 'triage' or 'escalate', not {tier!r}")

    backend = _analysis_backend()
    if backend == "hybrid":
        from rlens.versions import analyzer_pin, escalator_pin

        try:
            # **The tier picks the pin, and the caller cannot pass a model.** C4.4's whole
            # claim is that an escalated verdict came from a stronger model; a `model=`
            # parameter would make that claim checkable only by reading every call site.
            model = escalator_pin() if tier == "escalate" else analyzer_pin()
        except RuntimeError as exc:
            # **Replay needs the pin too, and that is deliberate.** A cassette records a
            # (model, prompt) pair. Replaying it while the environment declares a
            # different model would produce a report whose `judge_triage_pin` names one
            # model and whose labels came from another -- a provenance lie, and this
            # project's whole claim is that a published number is reproducible.
            #
            # `versions.analyzer_pin` raises about publishing numbers, which is the wrong
            # explanation when what you were doing was running the offline test suite.
            if os.environ.get("MOCK_LLM") == "1":
                raise ProviderError(
                    "MOCK_LLM=1 still needs MODEL_ANALYZE: a cassette records a (model, "
                    "prompt) pair and replay verifies both, so that a replayed report's "
                    "judge_triage_pin is true. It is a public model id, not a secret -- "
                    "set it in CI and in .env."
                ) from exc
            raise
    else:
        model = os.environ.get("LOCAL_MODEL", "")
        if not model:
            raise ProviderError("ANALYZER_BACKEND=local but LOCAL_MODEL is unset.")

    effort = os.environ.get("ANALYZE_REASONING_EFFORT", "low")
    cap = cap if cap is not None else int(os.environ.get("ANALYZE_MAX_OUTPUT_TOKENS", "16000"))
    timeout = timeout if timeout is not None else int(os.environ.get("ANALYSIS_DEADLINE_S", "110"))
    digest = request_digest(prompt, backend=backend, model=model)

    if os.environ.get("MOCK_LLM") == "1":
        if not cassette:
            raise ProviderError("MOCK_LLM=1 requires a cassette name")
        return _replay_analysis(cassette, digest)

    call = _analyze_hosted if backend == "hybrid" else _analyze_local
    started = time.time()
    for attempt in (1, 2):
        try:
            fields, _payload = _with_deadline(
                lambda: call(prompt, model, cap, effort, timeout), timeout
            )
            break
        except urllib.error.HTTPError as exc:
            # An HTTP error is the server answering. Retrying a 400 re-sends the same bad
            # request; the body is the only thing that says why, so it is surfaced rather
            # than swallowed into a generic transport retry.
            raise ProviderError(f"{model}: HTTP {exc.code}: {exc.read()[:400].decode()}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == 2:
                raise ProviderError(f"{model}: {type(exc).__name__}: {exc}") from exc
            time.sleep(0.5 + random.random())
    else:  # pragma: no cover -- the loop always breaks or raises
        raise ProviderError("unreachable")

    result = AnalysisResult(
        backend=backend,
        attempts=attempt,
        latency_ms=int((time.time() - started) * 1000),
        **fields,
    )
    if result.finish_reason == "length":
        raise AnalysisTruncated(
            f"{model}: the {cap}-token output cap bound (finish_reason=length) after "
            f"{result.completion_tokens} completion tokens. Raise ANALYZE_MAX_OUTPUT_TOKENS "
            f"or lower CLASSIFY_CHUNK_SIZE -- retrying reproduces this exactly (S3)."
        )
    if not result.text.strip():
        # S3 failure mode 1, kept distinct from a parse failure because the fix is
        # different: empty content with tokens billed means the model deliberated instead
        # of answering, and the lever is reasoning effort, not a smaller batch.
        raise ProviderError(
            f"{model}: empty content with {result.completion_tokens} completion tokens "
            f"billed at effort={effort!r}. The model spent its budget in the reasoning "
            f"channel (S3 failure mode 1). Lower ANALYZE_REASONING_EFFORT."
        )
    # M1-14. Recording happens HERE rather than in a separate harness that re-issues the
    # calls, because a cassette recorded by a different code path is a recording of that
    # path. `make record-cassettes` sets the flag and runs the ordinary pipeline, so what
    # is captured is exactly what production sends -- including the repair retry, which a
    # re-issuing recorder would never produce.
    if cassette and os.environ.get("RECORD_CASSETTES") == "1":
        record_analysis_cassette(cassette, result, request_digest=digest)
    return result
