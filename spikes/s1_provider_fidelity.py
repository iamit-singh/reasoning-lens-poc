"""S1 (M1-1) -- provider thinking-trace fidelity probe. Gate G0.

The question, in two halves, both of which matter:

  1. Does the API return **full, unsummarised** thinking text?   <- this is the product
  2. Are ``reasoning_tokens`` exposed in usage accounting?       <- this is B4 #7

The failure mode this script exists to prevent is S1 quietly succeeding: running one
prompt, seeing text that looks like thinking, and moving on. So the probe does not ask
"was there thinking text". It measures the returned thinking text's token count against
the provider's own ``reasoning_tokens`` and reports the ratio. A large gap is the
signature of summarisation.

Usage
-----
    make spike-s1 ARGS="--provider anthropic --model <exact-dated-id>"
    make spike-s1 ARGS="--list-candidates"
    make spike-s1 ARGS="--provider anthropic --model <id> --out docs/spikes/S1-raw"

Writes one JSON record per candidate to ``--out`` and prints the G0 table. The finding
is then written up by hand in ``docs/decisions/ADR-001-provider.md`` -- the ADR is the
deliverable, this script is the measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# The probe problem. One representative `multi_step` item: long enough to force
# several reasoning steps, checkable by exact match, and not memorisable as a
# stock puzzle. Kept here rather than in the bank because the bank (M1-4) does
# not exist in W1 and S1 must not wait for it.
# ---------------------------------------------------------------------------
PROBE_PROMPT = (
    "A warehouse ships items in cartons of 12 and pallets of 90 cartons.\n"
    "On Monday it shipped 7 pallets plus 43 loose cartons.\n"
    "On Tuesday it shipped 2/3 of Monday's total item count, rounded down to the "
    "nearest whole carton, with any remainder discarded.\n"
    "On Wednesday it shipped 150 fewer items than Tuesday.\n"
    "How many individual items were shipped across the three days in total?\n"
    "Show your reasoning, then give the final number on its own last line."
)

# Monday: 7*90+43 = 673 cartons = 8076 items
# Tuesday: 2/3 of 8076 = 5384 items = 448.67 cartons -> 448 cartons = 5376 items
# Wednesday: 5376-150 = 5226 items
# Total: 8076+5376+5226 = 18678
PROBE_KNOWN_ANSWER = 18678

#: Candidate tiers to probe. Filled from ADR-001's shortlist; the exact dated ids are
#: what G0 check 4 requires, so this list must never contain a floating alias.
CANDIDATES: dict[str, list[str]] = {
    "anthropic": [
        # e.g. "claude-opus-5", "claude-sonnet-5" -- pin the exact dated id at run time
    ],
}


@dataclass
class ProbeResult:
    """One provider/model probe. Serialised verbatim into the spike record."""

    provider: str
    model: str
    ok: bool = False
    error: str | None = None

    thinking_text_present: bool = False
    thinking_text_chars: int = 0
    thinking_text_tokens_estimated: int = 0
    reasoning_tokens_reported: int | None = None
    #: estimated tokens of returned text / reported reasoning tokens.
    #: ~1.0 => the text we got is the text the model was billed for (unsummarised).
    #: << 1.0 => the signature of summarisation. This is the number G0 check 2 turns on.
    fidelity_ratio: float | None = None

    answer_correct: bool | None = None
    usage_block: dict[str, Any] = field(default_factory=dict)
    provider_documents_summarisation: str | None = None
    raw_response_path: str | None = None


def estimate_tokens(text: str) -> int:
    """Rough token estimate, deliberately provider-agnostic.

    A real token count needs the provider's tokenizer. For G0's purpose -- detecting a
    *large* gap between returned text and billed reasoning tokens -- a ~4-chars-per-token
    estimate is sufficient, and its crudeness is recorded in the ADR rather than hidden.
    Refine with the provider tokenizer before quoting the ratio to 2 decimal places.
    """
    return max(1, round(len(text) / 4))


def probe_anthropic(model: str, out_dir: pathlib.Path) -> ProbeResult:
    """Probe an Anthropic model with extended thinking enabled."""
    result = ProbeResult(provider="anthropic", model=model)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        result.error = "ANTHROPIC_API_KEY is not set"
        return result
    try:
        import anthropic  # optional dep, imported only when probing
    except ImportError:
        result.error = "pip install 'reasoning-lens-analyzer[providers]' to probe anthropic"
        return result

    budget = int(os.environ.get("THINKING_BUDGET_TOKENS", "8000"))
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=budget + 2000,
            thinking={"type": "enabled", "budget_tokens": budget},
            messages=[{"role": "user", "content": PROBE_PROMPT}],
        )
    except Exception as exc:  # a spike records failures; it does not raise
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    payload = response.model_dump(mode="json")
    raw_path = out_dir / f"raw_anthropic_{model.replace('/', '_')}.json"
    raw_path.write_text(json.dumps(payload, indent=2))
    result.raw_response_path = str(raw_path)

    thinking = "".join(
        block.get("thinking", "")
        for block in payload.get("content", [])
        if block.get("type") == "thinking"
    )
    redacted = [b for b in payload.get("content", []) if b.get("type") == "redacted_thinking"]
    answer_text = "".join(
        block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
    )

    result.thinking_text_present = bool(thinking)
    result.thinking_text_chars = len(thinking)
    result.thinking_text_tokens_estimated = estimate_tokens(thinking) if thinking else 0
    result.usage_block = payload.get("usage", {}) or {}
    result.answer_correct = str(PROBE_KNOWN_ANSWER) in answer_text
    if redacted:
        result.provider_documents_summarisation = (
            f"{len(redacted)} redacted_thinking block(s) returned -- part of the trace is withheld"
        )

    # reasoning-token accounting: the field name differs across providers and tiers,
    # so look for any plausible spelling rather than asserting one.
    usage = result.usage_block
    for key in ("reasoning_tokens", "thinking_tokens", "output_reasoning_tokens"):
        if key in usage:
            result.reasoning_tokens_reported = int(usage[key])
            break
    else:
        nested = usage.get("output_tokens_details") or usage.get("completion_tokens_details") or {}
        if isinstance(nested, dict) and "reasoning_tokens" in nested:
            result.reasoning_tokens_reported = int(nested["reasoning_tokens"])

    if result.reasoning_tokens_reported:
        result.fidelity_ratio = round(
            result.thinking_text_tokens_estimated / result.reasoning_tokens_reported, 3
        )

    result.ok = True
    return result


PROBES = {"anthropic": probe_anthropic}


def render_g0_table(results: list[ProbeResult]) -> str:
    """Print the G0 checklist per candidate. Section 8.1 of the Month-1 breakdown."""
    lines = [
        "",
        "Gate G0 -- does the chosen provider return full, unsummarised thinking text?",
        "=" * 78,
    ]
    for r in results:
        lines.append(f"\n{r.provider} / {r.model}")
        if r.error:
            lines.append(f"  ERROR: {r.error}")
            continue
        ratio = r.fidelity_ratio
        checks = [
            ("1. thinking text returned via API", "PASS" if r.thinking_text_present else "FAIL"),
            (
                "2. thinking text is NOT a provider summary",
                "PASS"
                if ratio is not None and ratio >= 0.75
                else ("FAIL" if ratio is not None else "UNKNOWN -- no reasoning_tokens to compare"),
            ),
            (
                "3. reasoning_tokens exposed in usage",
                "PASS" if r.reasoning_tokens_reported else "FAIL",
            ),
            ("   (probe answer correct)", str(r.answer_correct)),
        ]
        for label, verdict in checks:
            lines.append(f"  {label:<48} {verdict}")
        lines.append(
            f"  returned thinking: {r.thinking_text_chars} chars "
            f"(~{r.thinking_text_tokens_estimated} tok) vs reported "
            f"reasoning_tokens={r.reasoning_tokens_reported} -> ratio={ratio}"
        )
        if r.provider_documents_summarisation:
            lines.append(f"  NOTE: {r.provider_documents_summarisation}")
    lines += [
        "",
        "Checks 4 (MODEL_PIN is an exact dated id), 5 (MODEL_TRIAGE / MODEL_ESCALATE named)",
        "and 6 (ADR committed) are human checks. Record all six in",
        "docs/decisions/ADR-001-provider.md -- the ADR is the G0 deliverable.",
        "",
        "A ratio well below 1.0 is the signature of summarisation. If no candidate passes",
        "check 2, fall back to a hosted open-weight R1-class model for arm 2 (B6.5) and",
        "decide it THIS WEEK, not in Month 3.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(PROBES), action="append", default=None)
    parser.add_argument("--model", action="append", default=None, help="exact dated model id")
    parser.add_argument("--out", default="docs/spikes/S1-raw", help="where raw responses land")
    parser.add_argument("--list-candidates", action="store_true")
    args = parser.parse_args(argv)

    if args.list_candidates:
        print(json.dumps(CANDIDATES, indent=2))
        return 0
    if not args.provider or not args.model:
        parser.error(
            "give at least one --provider and one --model (exact dated id, never an alias)"
        )

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[ProbeResult] = []
    for provider in args.provider:
        for model in args.model:
            if "latest" in model or model in {"claude-3-5-sonnet", "gpt-4o"}:
                print(
                    f"refusing to probe '{model}': G0 check 4 requires an exact dated id, "
                    "never a floating alias (C2.3).",
                    file=sys.stderr,
                )
                return 1
            print(f"probing {provider} / {model} ...", file=sys.stderr)
            results.append(PROBES[provider](model, out_dir))

    record = out_dir / "s1-results.json"
    record.write_text(json.dumps([asdict(r) for r in results], indent=2))
    print(render_g0_table(results))
    print(f"\nrecord: {record}")

    return 0 if any(r.ok and r.thinking_text_present for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
