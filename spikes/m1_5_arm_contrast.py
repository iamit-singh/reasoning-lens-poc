"""The arm contrast across the whole bank — the measurement ADR-004 asked for and
ADR-005 depends on. **Selects FE-1's featured comparison.**

Why this had to be run before ADR-005 could be accepted
-------------------------------------------------------
ADR-005 recommends withdrawing the trap floor and re-pointing FE-1's featured comparison
at the *difficulty* contrast instead of the trap contrast. That recommendation rests on a
claim: that some bank item has arm 1 wrong where arm 2 is right.

**The evidence for that claim was an ad-hoc probe, not a bank item.** M1-4's control run
used `--prompt`, and M1-5's 120 runs touched only the four trap items, on which both arms
were correct every time. So at the point ADR-005 was written, *no committed bank item was
known to separate the arms on accuracy* — and a decision to feature a contrast nobody has
observed in the corpus it will be drawn from is a decision resting on a probe.

`test_bank_answers.py` says as much in its own words: it asserts a structural proxy for
the `easy` control group and notes that *"whether the arms actually agree is a
MEASUREMENT, and it belongs to W3"*. This is that measurement.

What it measures
----------------
Every bank item, both arms, **pinned regime only** — `temperature=0` at the committed
seed, which is byte-stable and is the configuration the demo runs in. One run per cell is
therefore the honest form of five, and 14 items x 2 arms is 28 runs rather than 140.

Each cell is graded by the item's own declared checker (`rlens.checkers`), so the bank is
graded by the code that will grade the runs. Four outcomes per item:

| Pattern | What it means | Use |
| --- | --- | --- |
| **separated** | arm 1 wrong, arm 2 right | **FE-1's "thinking buys the answer" half** |
| **agreed** | both right | the ADR-004 control group — the cheaper arm was enough |
| **both wrong** | neither right | difficulty beyond the model; not an arm finding |
| **inverted** | arm 1 right, arm 2 wrong | deliberation talking itself out of a correct answer |

Token cost is recorded per cell, because the `agreed` rows only mean something with the
cost beside them: *the same answer, N times cheaper* is the claim B4 #7 actually makes.

Usage
-----
    make arm-contrast
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "analyzer/src"))

from rlens.checkers import check, sole_number
from rlens.llm import ProviderError, generate
from rlens.runner.arms import ARMS, messages_for
from rlens.runner.run import ArmResult
from rlens.versions import generation_pin

ROOT = pathlib.Path(__file__).parent.parent
BANK = ROOT / "problem-bank/items"
OUT_JSON = ROOT / "problem-bank/arm-contrast.json"
OUT_MD = ROOT / "problem-bank/arm-contrast.md"

PATTERNS = ("separated", "agreed", "both_wrong", "inverted", "incomplete")


class _TextOnly:
    """The one field `ArmResult.final_answer` reads."""

    def __init__(self, text: str) -> None:
        self.text = text


def final_answer(text: str) -> str:
    """The runner's own rule, not a second one. See `m1_5_trap_reproduction.final_answer`."""
    return ArmResult(
        strategy="", item_id="", trace_quality="full", completion=_TextOnly(text)
    ).final_answer


def outcome(item: dict[str, Any], answer: str) -> str:
    """`correct` | `unparsed` | `wrong`, by the item's own checker.

    `unparsed` stays separate from `wrong` for the reason M1-5 found: an unreadable answer
    counted as wrong understates accuracy, and accuracy is the number this table feeds.
    """
    if check(item["known_answer"], answer, item["checker"], item.get("tolerance")):
        return "correct"
    known = item["known_answer"]
    if isinstance(known, str) and sole_number(known) is not None and sole_number(answer) is None:
        return "unparsed"
    return "wrong"


def pattern(direct: str, thinking: str) -> str:
    if direct == "correct" and thinking == "correct":
        return "agreed"
    if direct != "correct" and thinking == "correct":
        return "separated"
    if direct == "correct" and thinking != "correct":
        return "inverted"
    if "unparsed" in (direct, thinking):
        return "incomplete"
    return "both_wrong"


def separated_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [r["item"] for r in rows if r["pattern"] == "separated"]


def run_cell(item: dict[str, Any], arm: str, pin: Any) -> dict[str, Any]:
    spec = ARMS[arm]
    try:
        c = generate(
            messages_for(spec, item["prompt"]),
            pin=pin,
            thinking=spec.thinking,
            reasoning_effort=spec.reasoning_effort,
        )
    except ProviderError as exc:
        return {"arm": arm, "outcome": "failed", "error": str(exc)}
    answer = final_answer(c.text)
    return {
        "arm": arm,
        "outcome": outcome(item, answer),
        "answer": answer,
        "reasoning_tokens": c.reasoning_tokens,
        "answer_tokens": c.answer_tokens,
        "text": c.text,
        "reasoning": c.reasoning,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="m1_5_arm_contrast")
    ap.add_argument("--item", help="one item only")
    ap.add_argument(
        "--dir",
        help="measure items from this directory instead of the bank. Candidate items are "
        "measured before they are promoted, for the same reason trap candidates are: "
        "lever L1 fixes the bank at 14 items, so 'author more' cannot mean 'grow the bank'.",
    )
    args = ap.parse_args(argv)

    os.environ["MOCK_LLM"] = "0"
    pin = generation_pin()
    missing = pin.unpinned_fields()
    if missing:
        raise SystemExit(f"generation pin incomplete, missing {', '.join(missing)}")

    source = pathlib.Path(args.dir) if args.dir else BANK
    items = [json.loads(p.read_text()) for p in sorted(source.glob("*.json"))]
    if args.item:
        items = [i for i in items if i["id"] == args.item]

    rows: list[dict[str, Any]] = []
    for item in items:
        cells = {arm: run_cell(item, arm, pin) for arm in ("direct", "thinking")}
        pat = pattern(cells["direct"]["outcome"], cells["thinking"]["outcome"])
        rows.append({"item": item["id"], "tags": item["tags"], "pattern": pat, "cells": cells})
        d, t = cells["direct"], cells["thinking"]
        print(
            f"  {item['id']:<7} {pat:<11} "
            f"direct={d['outcome']:<9}({d.get('reasoning_tokens')}tok) "
            f"thinking={t['outcome']:<9}({t.get('reasoning_tokens')}tok)"
        )

    payload = {
        "task": "M1-5 / ADR-004 control group",
        "recorded_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": "pinned",
        "pin": dataclasses.asdict(pin),
        "pin_fingerprint": pin.fingerprint(),
        "rows": rows,
    }
    if args.dir or args.item:
        # A partial run must not overwrite the bank-wide table it did not measure.
        print("\n(partial run: the committed table is left alone)")
    else:
        OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
        write_md(payload)
        print(f"\nraw -> {OUT_JSON}\nmd  -> {OUT_MD}")

    counts = {p: sum(1 for r in rows if r["pattern"] == p) for p in PATTERNS}
    print(f"\n{counts}")
    sep = separated_ids(rows)
    print(f"SEPARATED (FE-1 candidates): {', '.join(sep) or 'NONE'}")
    return 0 if sep else 1


def write_md(payload: dict[str, Any]) -> None:
    rows = payload["rows"]
    out: list[str] = []
    w = out.append
    w("<!-- Generated by spikes/m1_5_arm_contrast.py. Re-run with `make arm-contrast`. -->")
    w("")
    w("# The arm contrast across the bank — pinned regime")
    w("")
    w(
        f"**Recorded** {payload['recorded_utc']} · **pin** `{payload['pin_fingerprint']}` "
        f"(`{payload['pin']['model']}`) · **{len(rows) * 2} runs**, one per item per arm"
    )
    w("")
    w(
        "Pinned only — `temperature=0` at the committed seed is byte-stable and is the "
        "configuration the demo runs in, so one run per cell is the honest form of five."
    )
    w("")
    counts = {p: sum(1 for r in rows if r["pattern"] == p) for p in PATTERNS}
    separated = [r for r in rows if r["pattern"] == "separated"]
    w("## Verdict")
    w("")
    if separated:
        w(
            f"**{len(separated)} of {len(rows)} items separate the arms** "
            "(arm 1 wrong, arm 2 right): "
            + ", ".join("`" + r["item"] + "`" for r in separated)
            + ". FE-1's featured comparison has a bank item to draw on, and ADR-005's "
            "recommendation stands on corpus evidence rather than on an ad-hoc probe."
        )
    else:
        w(
            f"**No item separates the arms.** All {len(rows)} items land elsewhere: "
            f"{counts}. ADR-005's recommendation to re-point FE-1 at the difficulty "
            "contrast **cannot be satisfied from this bank as it stands** — the contrast "
            "exists on an ad-hoc probe and nowhere in the committed corpus. That is a "
            "finding for the reviewer, not something to work around."
        )
    w("")
    w(f"Patterns: {counts}")
    w("")
    w("## Per item")
    w("")
    w("| Item | Tags | Arm 1 (minimal) | tok | Arm 2 (thinking) | tok | Ratio | Pattern |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        d, t = r["cells"]["direct"], r["cells"]["thinking"]
        dt_, tt = d.get("reasoning_tokens"), t.get("reasoning_tokens")
        ratio = f"{tt / dt_:.1f}x" if dt_ and tt else "—"
        mark = {"separated": "**separated**", "agreed": "agreed"}.get(r["pattern"], r["pattern"])
        w(
            f"| `{r['item']}` | {', '.join(r['tags'])} | {d['outcome']} | {dt_} | "
            f"{t['outcome']} | {tt} | {ratio} | {mark} |"
        )
    w("")
    w(
        "**The `agreed` rows are the ADR-004 control group and they need the token columns "
        "beside them.** *The same answer, N times cheaper* is the claim B4 #7 makes; a "
        "bank of nothing but separating items would measure difficulty and call it "
        "strategy."
    )
    w("")
    OUT_MD.write_text("\n".join(out) + "\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
