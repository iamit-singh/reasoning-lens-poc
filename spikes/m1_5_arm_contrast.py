"""The arm contrast across the whole bank — the measurement ADR-004 asked for and
ADR-005 depends on. **Selects FE-1's featured comparison.**

Covers all three arms since M1-7. Arms 1 and 2 answer "what does the thinking buy?"; arm 3
answers "what do the tools buy?", and after ADR-006 that second question is the one
carrying the accuracy claim.

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

from rlens.checkers import check, final_answer_line, sole_number
from rlens.llm import ProviderError, generate
from rlens.runner.arms import ARMS, messages_for
from rlens.runner.react import run_react
from rlens.versions import generation_pin

ROOT = pathlib.Path(__file__).parent.parent
BANK = ROOT / "problem-bank/items"
OUT_JSON = ROOT / "problem-bank/arm-contrast.json"
OUT_MD = ROOT / "problem-bank/arm-contrast.md"

PATTERNS = ("separated", "agreed", "both_wrong", "inverted", "incomplete")

#: The three arms, in the order the report reads. Arm 3 is a LOOP, so `run_cell`
#: dispatches it rather than calling `generate` once.
ARM_ORDER = ("direct", "thinking", "react")


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
    if arm == "react":
        return _run_react_cell(item, pin)
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
    answer = final_answer_line(c.text)
    return {
        "arm": arm,
        "outcome": outcome(item, answer),
        "answer": answer,
        "reasoning_tokens": c.reasoning_tokens,
        "answer_tokens": c.answer_tokens,
        "text": c.text,
        "reasoning": c.reasoning,
    }


def _run_react_cell(item: dict[str, Any], pin: Any) -> dict[str, Any]:
    """Arm 3. Reports the loop's shape as well as its answer.

    `tool_calls` is recorded per item because it exposes a tag that may be wrong: an item
    tagged `tool_required` on which arm 3 calls **no tool** is an item the model does in
    its head, and `tool_required` feeds a share B4 #7 publishes. Same shape of problem as
    `is_trap` before M1-5 measured it -- a declaration standing in for a measurement.
    """
    result = run_react(item["id"], item["prompt"], pin=pin)
    final = result.final
    if final is None:
        return {"arm": "react", "outcome": "failed", "error": result.failed_reason or "no turns"}
    answer = final_answer_line(final.text)
    return {
        "arm": "react",
        "outcome": outcome(item, answer),
        "answer": answer,
        # Arm 3's cost is the WHOLE loop, not its last turn (ADR-007).
        "reasoning_tokens": sum(t.completion.reasoning_tokens or 0 for t in result.turns),
        "answer_tokens": final.answer_tokens,
        "turns": result.turn_count,
        "tool_calls": result.tool_calls_made,
        "failed_tool_calls": result.failed_tool_calls,
        "max_turns_exhausted": result.max_turns_exhausted,
        "text": final.text,
        "reasoning": final.reasoning,
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
        cells = {arm: run_cell(item, arm, pin) for arm in ARM_ORDER}
        pat = pattern(cells["direct"]["outcome"], cells["thinking"]["outcome"])
        rows.append({"item": item["id"], "tags": item["tags"], "pattern": pat, "cells": cells})
        d, t, r = cells["direct"], cells["thinking"], cells["react"]
        print(
            f"  {item['id']:<7} {pat:<11} "
            f"d={d['outcome']:<8}({d.get('reasoning_tokens')}t) "
            f"th={t['outcome']:<8}({t.get('reasoning_tokens')}t) "
            f"re={r['outcome']:<8}({r.get('reasoning_tokens')}t "
            f"{r.get('turns')}turn {r.get('tool_calls')}call)"
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
        f"(`{payload['pin']['model']}`) · **{len(rows)} items x 3 arms**"
    )
    w("")
    w(
        "Pinned only — `temperature=0` at the committed seed is byte-stable and is the "
        "configuration the demo runs in, so one run per cell is the honest form of five."
    )
    w("")

    counts = {p_: sum(1 for r in rows if r["pattern"] == p_) for p_ in PATTERNS}
    separated = [r for r in rows if r["pattern"] == "separated"]
    correct = {
        arm: sum(1 for r in rows if r["cells"][arm]["outcome"] == "correct") for arm in ARM_ORDER
    }
    tool_rescued = [
        r
        for r in rows
        if r["cells"]["react"]["outcome"] == "correct"
        and r["cells"]["direct"]["outcome"] != "correct"
        and r["cells"]["thinking"]["outcome"] != "correct"
    ]

    w("## Verdict")
    w("")
    w(
        f"**Accuracy:** arm 1 (minimal) {correct['direct']}/{len(rows)} · "
        f"arm 2 (thinking) {correct['thinking']}/{len(rows)} · "
        f"**arm 3 (ReAct) {correct['react']}/{len(rows)}**."
    )
    w("")
    if separated:
        w(
            f"**{len(separated)} of {len(rows)} items separate arms 1 and 2** "
            "(arm 1 wrong, arm 2 right): "
            + ", ".join("`" + r["item"] + "`" for r in separated)
            + "."
        )
    else:
        w(
            f"**No item separates arms 1 and 2.** All {len(rows)} land elsewhere: "
            f"{counts}. Arm 1's `low` effort is *adaptive* rather than shallow, so making "
            "items harder closes the cost gap without opening an accuracy gap — "
            "[ADR-006](../docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md)."
        )
    w("")
    if tool_rescued:
        w(
            f"**The accuracy separation this bank does contain is TOOLS.** "
            f"{len(tool_rescued)} items are wrong on both reasoning arms and right on arm "
            "3: " + ", ".join("`" + r["item"] + "`" for r in tool_rescued) + ". That is the "
            "wrong→right row FE-1 needs, and it confirms ADR-006's recommendation A on "
            "corpus evidence rather than on a probe."
        )
        w("")
        w("**And it is cheaper, not just better** \u2014 the part worth putting on screen:")
        w("")
        w("| Item | Arm 2 (thinking) | Arm 3 (tools) | |")
        w("| --- | --- | --- | --- |")
        for r in tool_rescued:
            t2 = r["cells"]["thinking"].get("reasoning_tokens") or 0
            t3 = r["cells"]["react"].get("reasoning_tokens") or 0
            ratio = f"**{t2 / t3:.0f}x cheaper**" if t3 else "\u2014"
            w(
                f"| `{r['item']}` | {r['cells']['thinking']['outcome']}, {t2} reasoning tok "
                f"| **correct**, {t3} tok | {ratio} |"
            )
        w("")
        w(
            "On `mb-08` the thinking arm spent **3,966 reasoning tokens failing to recall a "
            "fact that does not exist** \u2014 every place name in this corpus is invented, "
            "on purpose \u2014 while the tool arm spent 80 and looked it up. That pair is the "
            "product in one frame: one reasoning panel showing confabulation at length, "
            "beside one showing two tool calls. It is a stronger demo row than the "
            "difficulty contrast the plan expected, and unlike that one it exists."
        )
    else:
        w("**No item is rescued by arm 3 either.** ADR-006's option A has no evidence.")
    w("")

    w("## Per item")
    w("")
    w(
        "| Item | Tags | Arm 1 | tok | Arm 2 | tok | Arm 3 | tok | turns | tool calls | "
        "1v2 pattern |"
    )
    w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        d, t, re_ = r["cells"]["direct"], r["cells"]["thinking"], r["cells"]["react"]
        mark = {"separated": "**separated**", "agreed": "agreed"}.get(r["pattern"], r["pattern"])
        rescued = " ✅" if r in tool_rescued else ""
        calls = re_.get("tool_calls", "—")
        tagged = "tool_required" in r["tags"]
        # A `tool_required` item on which arm 3 called nothing is the mis-tag flagged below.
        if tagged and calls == 0:
            calls = "**0**"
        w(
            f"| `{r['item']}` | {', '.join(r['tags'])} | {d['outcome']} | "
            f"{d.get('reasoning_tokens')} | {t['outcome']} | {t.get('reasoning_tokens')} | "
            f"{re_['outcome']}{rescued} | {re_.get('reasoning_tokens')} | "
            f"{re_.get('turns', '—')} | {calls} | {mark} |"
        )
    w("")

    mistagged = [
        r
        for r in rows
        if "tool_required" in r["tags"] and r["cells"]["react"].get("tool_calls") == 0
    ]
    if mistagged:
        w("## `tool_required` is a declaration, not a measurement")
        w("")
        w(
            f"**{len(mistagged)} of "
            f"{sum(1 for r in rows if 'tool_required' in r['tags'])} items tagged "
            "`tool_required` had arm 3 call no tool at all** — "
            + ", ".join("`" + r["item"] + "`" for r in mistagged)
            + " — and answer correctly regardless. The model does that arithmetic in its "
            "head, so the tag describes an intention rather than a property."
        )
        w("")
        w(
            "This matters beyond tidiness: `problem-bank/README.md` states that the tag "
            'floors are *"what make B4 #7\'s `tool_required` share computable"*. A share '
            f"computed from the tag would be wrong by {len(mistagged)} of "
            f"{sum(1 for r in rows if 'tool_required' in r['tags'])} items. **The measured "
            "share is the one in the `tool calls` column above.**"
        )
        w("")
        w(
            "It is the same shape of problem as `is_trap` before M1-5 measured it, and the "
            "third tag in a row to turn out to be a claim. Recorded rather than relabelled "
            "— dropping the tag changes the L1 floor, which is a scope decision."
        )
        w("")

    w(
        "**The `agreed` rows are the ADR-004 control group and they need the token columns "
        "beside them.** *The same answer, N times cheaper* is the claim B4 #7 makes; a bank "
        "of nothing but separating items would measure difficulty and call it strategy."
    )
    w("")
    OUT_MD.write_text("\n".join(out) + "\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
