"""S6 -- local tool-calling reliability. Added by ADR-001. **Gates arm 3.**

Why this spike exists
---------------------
Arm 3 is a tool-using agent: the model must call a calculator and a lookup function. The
same-model rule (ADR-001) forbids moving that arm to OpenAI to get better tool calling,
because the three arms compare reasoning *strategies* -- different models per arm would
measure vendors instead, and the finding evaporates.

That makes local tool calling a **hard dependency of arm 3**, and it is the reason the
plan's own named fallback (a DeepSeek-R1 distill) was rejected: those models reason well
and fumble the call format. Discovering that in W3, after the arm is built, is expensive.
Discovering it in W2 costs half an hour.

What "reliable" means here
--------------------------
Not "it worked once". The agent loop makes several calls per problem, and one malformed
call derails the run. So this measures **repeatability**: N attempts per scenario, and the
pass rate. A model that calls correctly 70% of the time produces an agent arm that fails
most multi-step problems.

Usage
-----
    make spike-s6                       # 5 attempts per scenario
    make spike-s6 ARGS="--runs 10"
    make spike-s6 ARGS="--model qwen3:14b"   # test the approved fallback
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate an arithmetic expression and return the numeric result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "An arithmetic expression, e.g. '(7*90+43)*12'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Look up a fact by key from the curated corpus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The fact key to retrieve."}
                },
                "required": ["key"],
            },
        },
    },
]

# Each scenario states which tool a correct response must call. The third is the one that
# separates real tool use from pattern-matching: the model must choose, not just comply.
SCENARIOS: list[dict[str, str]] = [
    {
        "name": "calculator-forced",
        "prompt": "Using the calculator tool, compute (7*90+43)*12. Do not compute it yourself.",
        "expect": "calculator",
    },
    {
        "name": "lookup-forced",
        "prompt": "Using the lookup tool, retrieve the fact stored under the key 'carton_size'.",
        "expect": "lookup",
    },
    {
        "name": "tool-choice",
        "prompt": (
            "A pallet holds 90 cartons and each carton holds 12 items. "
            "How many items are on 7 pallets? Use the tools available to you."
        ),
        "expect": "calculator",
    },
    {
        "name": "no-tool-needed",
        "prompt": "Reply with the single word: ready. Do not call any tool.",
        "expect": "",
    },
]


def call(base: str, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": TOOLS,
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def evaluate(data: dict[str, Any], expect: str) -> tuple[bool, str]:
    """A call passes only if the right tool is named AND its arguments parse as JSON.

    Malformed arguments are the characteristic failure of weaker models: the tool name is
    right, the payload is prose or truncated JSON, and the agent loop dies on it. Counting
    those as passes would make this spike useless.
    """
    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    calls = msg.get("tool_calls") or []

    if not expect:
        return (not calls), (
            "no tool called, as required"
            if not calls
            else f"called {calls[0].get('function', {}).get('name')} when none was needed"
        )
    if not calls:
        return False, "no tool_calls in the response"

    fn = calls[0].get("function", {}) or {}
    name = fn.get("name", "")
    if name != expect:
        return False, f"called {name!r}, expected {expect!r}"

    raw = fn.get("arguments", "")
    if isinstance(raw, dict):
        return True, f"{name} with parsed object arguments"
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False, f"{name} called but arguments are not valid JSON: {str(raw)[:80]!r}"
    if not isinstance(parsed, dict) or not parsed:
        return False, f"{name} called with empty or non-object arguments"
    return True, f"{name} with valid arguments {parsed}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=os.environ.get("LOCAL_MODEL", "gpt-oss:20b"))
    ap.add_argument("--base", default=os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--threshold", type=float, default=0.9, help="required pass rate per scenario")
    ap.add_argument("--out", default="docs/spikes/S6-raw")
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict[str, Any]]] = {}
    for sc in SCENARIOS:
        print(f"{sc['name']}: ", end="", file=sys.stderr, flush=True)
        attempts: list[dict[str, Any]] = []
        for _ in range(args.runs):
            try:
                data = call(args.base, args.model, sc["prompt"], timeout=180)
                ok, why = evaluate(data, sc["expect"])
            except urllib.error.URLError as exc:
                print(
                    f"\ncannot reach {args.base}: {exc.reason}\n"
                    f"Is the model served? `ollama serve` then `ollama pull {args.model}`",
                    file=sys.stderr,
                )
                return 2
            except Exception as exc:
                ok, why = False, f"{type(exc).__name__}: {exc}"
            attempts.append({"ok": ok, "why": why})
            print("." if ok else "x", end="", file=sys.stderr, flush=True)
        print("", file=sys.stderr)
        results[sc["name"]] = attempts

    record = {
        "model": args.model,
        "runs": args.runs,
        "threshold": args.threshold,
        "results": results,
    }
    (out / "s6-results.json").write_text(json.dumps(record, indent=2))

    print(f"\nS6 -- local tool-calling reliability: {args.model}")
    print("=" * 78)
    worst = 1.0
    for name, attempts in results.items():
        rate = sum(a["ok"] for a in attempts) / len(attempts)
        worst = min(worst, rate)
        mark = "PASS" if rate >= args.threshold else "FAIL"
        print(
            f"  {name:<20} {sum(a['ok'] for a in attempts)}/{len(attempts)}  {rate:>5.0%}  {mark}"
        )
        for why in {a["why"] for a in attempts if not a["ok"]}:
            print(f"      failure: {why}")

    print(f"\nworst scenario: {worst:.0%} (threshold {args.threshold:.0%})")
    if worst >= args.threshold:
        print("\nARM 3 IS BUILDABLE on this model. Record the result in ADR-001.")
        return 0
    print(
        "\nARM 3 IS AT RISK on this model.\n"
        "  1. Try the approved fallback: --model qwen3:14b (stronger at tool calling).\n"
        "  2. Do NOT move arm 3 to OpenAI -- that violates the same-model rule in ADR-001\n"
        "     and turns the comparison from 'strategies' into 'vendors'.\n"
        "  3. If no local model holds the contract, drop to a two-arm comparison and say so\n"
        "     plainly. A smaller honest claim beats a three-arm result that measures vendors."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
