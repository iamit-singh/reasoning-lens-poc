"""S1 -- reasoning-trace fidelity, re-scoped by ADR-001. Gate G0.

The original question was "which hosted provider returns unsummarised thinking text".
ADR-001 answered it architecturally: generation moved to a **local** model, where the raw
trace is in the response because there is no server to withhold it.

So this spike now measures two different things:

  local   -- is the full raw reasoning actually recoverable, and countable exactly?
  openai  -- what does it expose? Summary only, as expected, or more?

The second half still matters. "OpenAI summarises its reasoning" is a strong expectation,
not a measurement, and this project's whole thesis is that the difference between those two
words matters. A finding either way is cheap; an assumption is not.

Usage
-----
    make spike-s1                      # both, using .env
    make spike-s1 ARGS="--only local"
    make spike-s1 ARGS="--only openai"

Writes raw responses and a JSON record to --out, then prints the G0 table.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

# One representative multi-step problem: long enough to force several reasoning steps,
# checkable by exact match, not memorisable as a stock puzzle. Kept here rather than in the
# problem bank because the bank does not exist until W2 and this spike must not wait.
PROBE_PROMPT = (
    "A warehouse ships items in cartons of 12 and pallets of 90 cartons.\n"
    "On Monday it shipped 7 pallets plus 43 loose cartons.\n"
    "On Tuesday it shipped 2/3 of Monday's total item count, rounded down to the "
    "nearest whole carton, with any remainder discarded.\n"
    "On Wednesday it shipped 150 fewer items than Tuesday.\n"
    "How many individual items were shipped across the three days in total?\n"
    "Show your reasoning, then give the final number on its own last line."
)
# Monday 7*90+43 = 673 cartons = 8076 items; Tuesday 2/3 -> 448 cartons = 5376;
# Wednesday 5226; total 18678.
PROBE_ANSWER = 18678


@dataclass
class Probe:
    """One target's result. Serialised verbatim into the spike record."""

    target: str
    model: str
    ok: bool = False
    error: str | None = None

    reasoning_text_present: bool = False
    reasoning_text_chars: int = 0
    reasoning_tokens_reported: int | None = None
    #: G0 check 2. Counted locally with the model's own tokenizer -- exact, where a
    #: provider's number is at best rounded and at worst absent.
    tokenizer: str | None = None
    reasoning_tokens_exact: int | None = None
    answer_tokens_exact: int | None = None
    #: reported completion_tokens minus (reasoning + answer). The harmony format wraps
    #: each channel in structural tokens which the runtime counts and the extracted text
    #: does not contain, so a small positive residual is expected and is NOT an error.
    #: A large or negative residual means the encoding is wrong for this model.
    structural_token_residual: int | None = None
    reasoning_token_share: float | None = None
    #: chars-per-reported-token. ~3-5 means the text we hold is the text that was billed.
    #: Far above that means we are holding a summary of something longer.
    chars_per_reasoning_token: float | None = None
    verdict: str = ""

    answer_correct: bool | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    raw_path: str | None = None


def _post(
    url: str, payload: dict[str, Any], *, api_key: str | None, timeout: int
) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


#: Which tiktoken encoding belongs to which local model. Deliberately a lookup and not a
#: default: gpt-oss uses harmony, the approved fallback qwen3 does not, and silently
#: counting one model's text with another's tokenizer produces a plausible wrong number --
#: the worst kind. An unknown model reports "no count", which is honest.
TOKENIZERS: dict[str, str] = {"gpt-oss": "o200k_harmony"}


def _encoding_for(model: str) -> str | None:
    """The encoding for this model, or None if we do not know it.

    ``LOCAL_TOKENIZER`` overrides, because it is part of the pin: swapping the model
    without swapping the tokenizer is exactly the mistake this refuses to make quietly.
    """
    override = os.environ.get("LOCAL_TOKENIZER")
    if override:
        return override
    for prefix, enc in TOKENIZERS.items():
        if model.startswith(prefix):
            return enc
    return None


def _count_exact(p: Probe, reasoning: str, answer: str) -> None:
    """Count reasoning and answer tokens with the model's own tokenizer (G0 check 2)."""
    enc_name = _encoding_for(p.model)
    if not enc_name:
        p.tokenizer = None
        return
    try:
        import tiktoken

        enc = tiktoken.get_encoding(enc_name)
    except Exception as exc:  # a spike records failures; it does not raise
        p.tokenizer = f"{enc_name} (unavailable: {type(exc).__name__})"
        return

    p.tokenizer = enc_name
    p.reasoning_tokens_exact = len(enc.encode(reasoning))
    p.answer_tokens_exact = len(enc.encode(answer))
    total = p.reasoning_tokens_exact + p.answer_tokens_exact
    if total:
        p.reasoning_token_share = round(p.reasoning_tokens_exact / total, 3)
    billed = p.usage.get("completion_tokens")
    if isinstance(billed, int):
        p.structural_token_residual = billed - total


def _dig(usage: dict[str, Any]) -> int | None:
    """Find a reasoning-token count under any of the spellings providers use."""
    for key in ("reasoning_tokens", "thinking_tokens"):
        if isinstance(usage.get(key), int):
            return usage[key]
    for nest in ("completion_tokens_details", "output_tokens_details"):
        inner = usage.get(nest)
        if isinstance(inner, dict) and isinstance(inner.get("reasoning_tokens"), int):
            return inner["reasoning_tokens"]
    return None


def probe_local(out: pathlib.Path, timeout: int) -> Probe:
    """The local generation model, via its OpenAI-compatible endpoint.

    Reasoning arrives either as a ``reasoning``/``reasoning_content`` field or inline in
    ``<think>`` tags, depending on the model and the runtime. Both are accepted; which one
    it was is part of the finding, because the segmenter has to strip it consistently.
    """
    base = os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")
    model = os.environ.get("LOCAL_MODEL", "gpt-oss:20b")
    p = Probe(target="local", model=model)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
        "temperature": float(os.environ.get("GEN_TEMPERATURE", "0")),
        "seed": int(os.environ.get("GEN_SEED", "0")),
        "stream": False,
    }
    effort = os.environ.get("LOCAL_REASONING_EFFORT")
    if effort:
        payload["reasoning_effort"] = effort

    try:
        data = _post(f"{base.rstrip('/')}/chat/completions", payload, api_key=None, timeout=timeout)
    except urllib.error.URLError as exc:
        p.error = (
            f"cannot reach {base}: {exc.reason}. Is the model served? "
            f"`ollama serve` then `ollama pull {model}`"
        )
        return p
    except Exception as exc:  # a spike records failures; it does not raise
        p.error = f"{type(exc).__name__}: {exc}"
        return p

    (out / "raw_local.json").write_text(json.dumps(data, indent=2))
    p.raw_path = str(out / "raw_local.json")

    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    text = msg.get("content") or ""
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    inline = ""
    if not reasoning and "<think>" in text:
        inline = text.split("<think>", 1)[1].split("</think>", 1)[0]
    trace = reasoning or inline

    p.reasoning_text_present = bool(trace)
    p.reasoning_text_chars = len(trace)
    p.usage = data.get("usage") or {}
    p.reasoning_tokens_reported = _dig(p.usage)
    p.answer_correct = str(PROBE_ANSWER) in text
    _count_exact(p, trace, text)
    if p.reasoning_tokens_reported:
        p.chars_per_reasoning_token = round(len(trace) / p.reasoning_tokens_reported, 2)

    if not trace:
        p.verdict = "FAIL -- no reasoning trace recoverable. Arm 2 is not buildable on this model."
    else:
        where = "a reasoning field" if reasoning else "inline <think> tags"
        p.verdict = f"PASS -- full raw trace recovered from {where} ({len(trace)} chars)."
        if not p.reasoning_tokens_reported:
            if p.reasoning_tokens_exact is not None:
                p.verdict += (
                    f" No reasoning_tokens in usage, but counted exactly locally:"
                    f" {p.reasoning_tokens_exact} reasoning tokens via {p.tokenizer}."
                    " G0 check 2 is satisfied by the local count, not by the provider."
                )
            else:
                p.verdict += (
                    " Token count absent from usage AND no local tokenizer available --"
                    " G0 check 2 is NOT satisfied. Cost-of-thought would be an estimate."
                )
    p.ok = True
    return p


def probe_openai(out: pathlib.Path, timeout: int) -> Probe:
    """OpenAI, as the analyzer tier -- and to test the summarisation expectation."""
    model = os.environ.get("MODEL_ANALYZE", "")
    p = Probe(target="openai", model=model or "<MODEL_ANALYZE unset>")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        p.error = "OPENAI_API_KEY is not set"
        return p
    if not model:
        p.error = "MODEL_ANALYZE is not set -- it must be an exact dated id (ADR-001)"
        return p

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
    }
    try:
        data = _post(
            "https://api.openai.com/v1/chat/completions", payload, api_key=key, timeout=timeout
        )
    except urllib.error.HTTPError as exc:
        p.error = f"HTTP {exc.code}: {exc.read().decode()[:300]}"
        return p
    except Exception as exc:
        p.error = f"{type(exc).__name__}: {exc}"
        return p

    (out / "raw_openai.json").write_text(json.dumps(data, indent=2))
    p.raw_path = str(out / "raw_openai.json")

    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    text = msg.get("content") or ""
    trace = msg.get("reasoning") or msg.get("reasoning_content") or ""

    p.reasoning_text_present = bool(trace)
    p.reasoning_text_chars = len(trace)
    p.usage = data.get("usage") or {}
    p.reasoning_tokens_reported = _dig(p.usage)
    p.answer_correct = str(PROBE_ANSWER) in text
    if trace and p.reasoning_tokens_reported:
        p.chars_per_reasoning_token = round(len(trace) / p.reasoning_tokens_reported, 2)

    billed = p.reasoning_tokens_reported
    if not trace and billed:
        p.verdict = (
            f"EXPECTED -- {billed} reasoning tokens billed, zero returned as text. "
            "The chain stays server-side. Confirms ADR-001: OpenAI cannot serve arm 2."
        )
    elif not trace and not billed:
        p.verdict = "No reasoning text and no reasoning-token count -- not a reasoning model."
    elif trace and billed and len(trace) / billed < 2.0:
        p.verdict = (
            f"SUMMARY -- {len(trace)} chars of text against {billed} billed tokens "
            "(~<2 chars/token is far too dense for real text). A summary of a longer chain."
        )
    else:
        p.verdict = (
            "UNEXPECTED -- reasoning text returned at a plausible density. Worth a second "
            "look: if OpenAI exposes real traces, that is a finding. It does not reverse "
            "ADR-001 (the local model is preferred on reproducibility grounds), but record it."
        )
    p.ok = True
    return p


def render(probes: list[Probe]) -> str:
    lines = ["", "Gate G0 -- reasoning-trace fidelity (re-scoped by ADR-001)", "=" * 78]
    for p in probes:
        lines.append(f"\n[{p.target}] {p.model}")
        if p.error:
            lines.append(f"  ERROR: {p.error}")
            continue
        lines += [
            f"  raw reasoning text present    {p.reasoning_text_present}",
            f"  reasoning text length         {p.reasoning_text_chars} chars",
            f"  reasoning tokens billed       {p.reasoning_tokens_reported}",
            f"  chars per billed token        {p.chars_per_reasoning_token}",
            f"  probe answer correct          {p.answer_correct}",
        ]
        if p.tokenizer and p.reasoning_tokens_exact is not None:
            share = (
                f"{p.reasoning_token_share:.1%}" if p.reasoning_token_share is not None else "n/a"
            )
            lines += [
                f"  tokenizer (G0 check 2)        {p.tokenizer}",
                f"  reasoning tokens EXACT        {p.reasoning_tokens_exact}",
                f"  answer tokens exact           {p.answer_tokens_exact}",
                f"  reasoning share of output     {share}",
                f"  structural residual           {p.structural_token_residual}"
                "  (billed - counted; small + is the harmony channel wrapper)",
            ]
        elif p.tokenizer:
            lines.append(f"  tokenizer (G0 check 2)        {p.tokenizer} -- NO COUNT")
        else:
            lines.append(
                "  tokenizer (G0 check 2)        UNKNOWN for this model -- no exact count."
                " Set LOCAL_TOKENIZER; it is part of the pin"
            )
        lines.append(f"  -> {p.verdict}")
    lines += [
        "",
        "G0 also requires: the tool contract held (run spike-s6 -- it gates arm 3), the",
        "generation pin tuple recorded (`make pin-local`), and the analyzer tier pinned to an",
        "exact dated id. Record all of it in docs/decisions/ADR-001-provider.md.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=["local", "openai"], default=None)
    ap.add_argument("--out", default="docs/spikes/S1-raw")
    ap.add_argument("--timeout", type=int, default=300, help="local generation can be slow")
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    targets = [args.only] if args.only else ["local", "openai"]
    probes = []
    for t in targets:
        print(f"probing {t} ...", file=sys.stderr)
        probe = probe_local if t == "local" else probe_openai
        probes.append(probe(out, args.timeout))

    (out / "s1-results.json").write_text(json.dumps([asdict(p) for p in probes], indent=2))
    print(render(probes))
    print(f"\nrecord: {out / 's1-results.json'}")

    # Only the local probe can fail the gate: it is the one arm 2 depends on.
    local = next((p for p in probes if p.target == "local"), None)
    return 0 if local is None or (local.ok and local.reasoning_text_present) else 1


if __name__ == "__main__":
    raise SystemExit(main())
