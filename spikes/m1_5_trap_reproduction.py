"""M1-5 -- trap reproduction. **Earns the `is_trap` tag that M1-4 declared.**

Not a C13.1 spike, despite living beside them: the S-harnesses answer a yes/no about the
runtime, and this one measures the bank. It sits here because this is where the repo keeps
standalone harnesses that talk to the live model and write a committed finding, and
because it must not become analyzer code -- it reads `problem-bank/` as data (I1).

What M1-5 asks, and why it cannot be run as written
---------------------------------------------------
The DoD is "each trap reproduces a plausible wrong chain in >= 3 of 5 runs". **Five runs
of what?** At the committed pin the answer is "the same run, five times": `GEN_TEMPERATURE=0`
with a fixed `GEN_SEED`, and `llm.generate` sends both on every call for both arms. Measured
before writing this harness -- two thinking-arm runs of `mb-13` came back byte-identical,
259 reasoning tokens each. A hit count out of 5 under those settings can only ever be 0 or 5,
and calling that "3 of 5" would be a number with no variance in it.

So the harness measures two regimes and reports both, because they answer different questions:

* **pinned** -- one run at the committed pin. *Will the trap fire in the configuration the
  demo actually runs in?* Binary, and verified byte-stable, so one run is the honest form of
  five. This is the stronger fact for FE-1: the demo is greedy-decoded, so a trap that fires
  here fires on stage.
* **sampled** -- five runs at `TRAP_TEMPERATURE` (default 1.0, the runtime's own default
  rather than a number invented here) with five varied seeds. *How fragile is that binary?*
  This is the regime the DoD's "of 5" is measured in, because it is the only one where the
  denominator means anything.

A trap that fires pinned but hits 1/5 sampled has not failed -- it has told you it is sitting
on a knife edge, and one re-pull of the weights can flip it with nothing to warn you. That is
worth knowing before it is the featured comparison on stage.

Both arms are measured. The trap targets **arm 1**: B4 #7's claim is that minimal reasoning
falls for what deliberation catches, so a trap that fires on arm 1 and is corrected by arm 2
is the best possible outcome -- that pair *is* the FE-1 featured comparison. A trap that
fires on both arms is an item the model simply cannot do, and a trap that fires on neither is
not a trap. The log names which of the three each candidate turned out to be.

Detection is exact, not judged
------------------------------
Each trap item declares `trap_answers` -- the specific wrong answers its `trap_note` argues
for -- and a run counts as a reproduction when the item's own checker accepts one of them.
Reusing `rlens.checkers` is the same rule M1-4 set: a bank graded by different code than the
code that grades the runs is graded against nothing. An LLM judge here would put a
measurement error inside the measurement.

Usage
-----
    make traps                        # 5 sampled runs per candidate per arm
    make traps ARGS="--runs 10"
    make traps ARGS="--item mb-11"    # one candidate
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "analyzer/src"))

from rlens.checkers import check, sole_number
from rlens.llm import ProviderError, generate
from rlens.runner.arms import ARMS, messages_for
from rlens.runner.run import ArmResult
from rlens.versions import GenerationPin, generation_pin

ROOT = pathlib.Path(__file__).parent.parent
BANK = ROOT / "problem-bank/items"
TRAPS_DIR = ROOT / "problem-bank/traps"
CANDIDATES = TRAPS_DIR / "candidates"
RUNS_PATH = TRAPS_DIR / "runs.json"
LOG_PATH = TRAPS_DIR / "reproduction-log.md"

#: M1-5's threshold, and the plan is explicit that it does not move: "a trap that
#: reproduces 2 of 5 times is a trap that fails on stage 60% of the time". If fewer than
#: THRESHOLD_TRAPS candidates clear it, author more candidates.
HITS_REQUIRED = 3
SAMPLED_RUNS = 5
THRESHOLD_TRAPS = 3

#: Seeds for the sampled regime. Written down rather than randomised: the fragility number
#: is evidence, and evidence that cannot be re-run is an anecdote. Derived from the pin's
#: own seed so they travel with it.
SEED_OFFSETS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

#: `unparsed` is not a bin for "wrong in some other way". A run whose answer could not
#: be READ is a different fact from a run that was wrong, and folding the first into the
#: second understates accuracy for free -- see `grade`.
OUTCOMES = ("correct", "trap", "other", "unparsed")

POOLS = {"items": None, "candidates": None, "all": None}


def load_traps(pool: str = "all", only: str | None = None) -> list[dict[str, Any]]:
    """Trap candidates from the bank, from the candidate pool, or both.

    **Candidates live outside `problem-bank/items/` on purpose.** Lever L1 fixes the bank
    at exactly 14 items and `test_bank_answers.py` asserts that count, so authoring more
    candidates -- which is precisely what M1-5 instructs on failure -- cannot mean growing
    the bank. A candidate is measured here and only *promoted* into `items/` once it has
    earned its tag, replacing a declared trap that did not. The bank stays the measured
    corpus rather than a pile of things that were tried.
    """
    traps: list[dict[str, Any]] = []
    sources = {"items": BANK, "candidates": CANDIDATES}
    for name, directory in sources.items():
        if pool not in (name, "all") or not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            item = json.loads(path.read_text())
            if not item.get("is_trap"):
                continue
            # A retired declaration is its own group: it was M1-4's claim, it lives in
            # the candidate directory now, and calling it "authored in M1-5" would
            # misattribute both the claim and its withdrawal.
            item["_pool"] = "retired" if item.get("retired_from") else name
            traps.append(item)
    if only:
        traps = [i for i in traps if i["id"] == only]
    for item in traps:
        validate(item)
    return traps


def validate(item: dict[str, Any]) -> None:
    """An authoring defect must not reach the measurement wearing a result's clothes.

    A candidate whose checker rejects its own correct answer measures as a trap that
    reproduces every time; one whose checker ACCEPTS its trap answer measures as a trap
    that never reproduces. Both look like findings. This is the same contract
    `test_bank_answers.py` holds the bank to, applied to the candidate pool, which that
    test does not see.
    """
    tol = item.get("tolerance")
    if not item.get("trap_answers"):
        raise SystemExit(
            f"{item['id']}: is_trap with no `trap_answers`. M1-5 cannot measure "
            f"reproduction against a wrong chain nobody wrote down -- otherwise any "
            f"wrong answer counts and the 3/5 threshold means nothing."
        )
    if not check(item["known_answer"], item["known_answer"], item["checker"], tol):
        raise SystemExit(f"{item['id']}: its own checker rejects its own known_answer")
    for trap in item["trap_answers"]:
        if check(item["known_answer"], trap, item["checker"], tol):
            raise SystemExit(
                f"{item['id']}: checker accepts trap answer {trap!r} as correct, so this "
                f"trap could never be observed to reproduce"
            )


def final_answer(text: str) -> str:
    """Delegated to the runner's own rule, deliberately.

    A harness that read answers more generously than the pipeline does would measure a
    trap the pipeline will never see. `ArmResult.final_answer` is the one rule, and M1-5
    fixed it rather than working around it: the naive "last non-empty line" returned the
    LaTeX delimiter `\\]` on `mb-11`, scoring a correct answer unreadable.
    """
    return ArmResult(
        strategy="", item_id="", trace_quality="full", completion=_TextOnly(text)
    ).final_answer


class _TextOnly:
    """The one field `final_answer` reads. Keeps this harness off the Completion
    constructor, whose eighteen fields are `llm.py`'s business and not ours."""

    def __init__(self, text: str) -> None:
        self.text = text


def grade(item: dict[str, Any], answer: str) -> str:
    """`correct` | `trap` | `unparsed` | `other`, by the item's own declared checker.

    `other` is not a rounding bin. A model that is wrong in an unpredictable way has not
    fallen for the trap -- it has just missed -- and counting that as a reproduction would
    let any hard item pass as a trap.

    `unparsed` is the distinction M1-5 had to add. `mb-11`'s thinking arm put its answer
    inside a LaTeX display block whose content line carries four numbers; the answer is
    not readable without guessing which one it meant, and guessing is exactly what a
    grader must not do -- the same willingness would pick the right number out of a
    *wrong* chain. So it is reported as unreadable. **This matters beyond M1-5: an
    unreadable run counted as wrong silently understates accuracy, and accuracy is
    M1-9/M1-10's number to publish.**
    """
    checker, tol = item["checker"], item.get("tolerance")
    if check(item["known_answer"], answer, checker, tol):
        return "correct"
    if any(check(t, answer, checker, tol) for t in item["trap_answers"]):
        return "trap"
    if sole_number(item["known_answer"]) is not None and sole_number(answer) is None:
        return "unparsed"
    return "other"


def run_once(
    item: dict[str, Any], arm: str, pin: GenerationPin, regime: str, seed: int
) -> dict[str, Any]:
    spec = ARMS[arm]
    run_id = f"{item['id']}.{arm}.{regime}.s{seed}"
    started = time.time()
    try:
        c = generate(
            messages_for(spec, item["prompt"]),
            pin=pin,
            thinking=spec.thinking,
            reasoning_effort=spec.reasoning_effort,
        )
    except ProviderError as exc:
        # A failed run is recorded, never silently dropped: a denominator that shrinks
        # when calls fail turns a flaky runtime into a better-looking trap.
        return {
            "run_id": run_id,
            "item": item["id"],
            "arm": arm,
            "regime": regime,
            "seed": seed,
            "temperature": pin.temperature,
            "outcome": "failed",
            "error": str(exc),
            "elapsed_s": round(time.time() - started, 2),
        }
    answer = final_answer(c.text)
    return {
        "run_id": run_id,
        "item": item["id"],
        "arm": arm,
        "regime": regime,
        "seed": seed,
        "temperature": pin.temperature,
        "outcome": grade(item, answer),
        "answer": answer,
        "reasoning_tokens": c.reasoning_tokens,
        "answer_tokens": c.answer_tokens,
        "finish_reason": c.finish_reason,
        "budget_bound": c.budget_bound,
        "pin_fingerprint": pin.fingerprint(),
        # The chain is the evidence -- "a plausible wrong chain" is the thing being
        # claimed, so the text that makes the claim checkable is committed with it.
        "reasoning": c.reasoning,
        "text": c.text,
        "content_sha": hashlib.sha256((c.reasoning + "\x1f" + c.text).encode()).hexdigest()[:12],
        "elapsed_s": round(time.time() - started, 2),
    }


def tally(runs: list[dict[str, Any]], item_id: str, arm: str, regime: str) -> dict[str, int]:
    sel = [r for r in runs if r["item"] == item_id and r["arm"] == arm and r["regime"] == regime]
    counts = {o: sum(1 for r in sel if r["outcome"] == o) for o in (*OUTCOMES, "failed")}
    counts["n"] = len(sel)
    return counts


def earned_arms(runs: list[dict[str, Any]], item_id: str) -> list[str]:
    """Arms on which this candidate EARNED its tag.

    Both regimes, same arm. Pinned alone is one point in sampling space with nothing to
    say how close the edge is; sampled alone does not describe the demo, which is
    greedy-decoded.
    """
    out = []
    for arm in sorted({r["arm"] for r in runs if r["item"] == item_id}):
        pinned = tally(runs, item_id, arm, "pinned")
        sampled = tally(runs, item_id, arm, "sampled")
        if pinned["trap"] >= 1 and sampled["trap"] >= HITS_REQUIRED:
            out.append(arm)
    return out


def merge(previous: list[dict[str, Any]], fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accumulate evidence across invocations, newest run winning on `run_id`.

    M1-5 is measured in stages -- screen on arm 1, then confirm the contrast on arm 2 for
    whatever survived -- and each stage is a separate invocation. Overwriting the file
    each time would make the log describe only the last stage.
    """
    by_id = {r["run_id"]: r for r in previous}
    by_id.update({r["run_id"]: r for r in fresh})
    return sorted(by_id.values(), key=lambda r: r["run_id"])


def regrade(runs: list[dict[str, Any]], traps: list[dict[str, Any]]) -> int:
    """Re-derive every stored outcome with the CURRENT grader. No model calls.

    The full response text is committed with each run, which makes this possible -- and
    necessary. M1-5 changed both the answer extractor and the checker mid-measurement, and
    a log whose rows were graded by two different graders is not a measurement of anything.
    Re-grading offline is also the cheaper half of that honesty: 48 runs, no GPU.
    """
    by_id = {i["id"]: i for i in traps}
    changed = 0
    for r in runs:
        item = by_id.get(r["item"])
        if item is None or "text" not in r:
            continue
        answer = final_answer(r["text"])
        outcome = grade(item, answer)
        if (r.get("answer"), r.get("outcome")) != (answer, outcome):
            print(f"  regrade {r['run_id']:<34} {r.get('outcome')} -> {outcome}   {answer[:46]!r}")
            r["answer"], r["outcome"] = answer, outcome
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="m1_5_trap_reproduction", description="M1-5")
    ap.add_argument("--item", help="one candidate only")
    ap.add_argument("--pool", choices=("items", "candidates", "all"), default="all")
    ap.add_argument("--runs", type=int, default=SAMPLED_RUNS, help="sampled runs per arm")
    ap.add_argument("--arm", action="append", choices=sorted(ARMS), help="repeatable")
    ap.add_argument(
        "--regrade",
        action="store_true",
        help="re-grade the committed runs with the current grader and rewrite the log. "
        "No model calls -- use after a change to the checker or the answer extractor.",
    )
    ap.add_argument("--fresh", action="store_true", help="discard accumulated runs first")
    args = ap.parse_args(argv)

    if args.runs > len(SEED_OFFSETS):
        ap.error(f"--runs above {len(SEED_OFFSETS)} needs more declared seeds; see SEED_OFFSETS")
    os.environ["MOCK_LLM"] = "0"  # a cassette replays one answer N times; that is not a sample

    pin = generation_pin()
    missing = pin.unpinned_fields()
    if missing:
        raise SystemExit(
            f"generation pin incomplete, missing {', '.join(missing)}. Run `make pin-local`. "
            "A reproduction rate measured on an unpinned model is not evidence (C2.3/I3)."
        )
    sampled_temp = float(os.environ.get("TRAP_TEMPERATURE", "1.0"))
    if sampled_temp <= 0:
        raise SystemExit(
            f"TRAP_TEMPERATURE={sampled_temp} is greedy decoding: five runs would be one run "
            "five times, and the sampled regime would report a hit count with no variance."
        )

    # The log always describes every candidate with evidence on file, not just the ones
    # this invocation touched -- otherwise a staged measurement reads as a shrinking bank.
    all_traps = load_traps("all")
    measured = load_traps(args.pool, args.item)
    if not measured and not args.regrade:
        raise SystemExit("no trap candidates found")

    previous: list[dict[str, Any]] = []
    if RUNS_PATH.exists() and not args.fresh:
        previous = json.loads(RUNS_PATH.read_text()).get("runs", [])

    fresh: list[dict[str, Any]] = []
    if not args.regrade:
        arms = args.arm or sorted(ARMS)
        for item in measured:
            for arm in arms:
                # Pinned: the demo's own configuration. One run, because it was measured
                # to be byte-stable -- see the module docstring.
                r = run_once(item, arm, pin, "pinned", pin.seed)
                fresh.append(r)
                print(f"  {r['run_id']:<34} {r['outcome']:<9} {r.get('answer', '')[:42]!r}")
                for off in SEED_OFFSETS[: args.runs]:
                    seed = pin.seed + off
                    sampled_pin = dataclasses.replace(pin, temperature=sampled_temp, seed=seed)
                    r = run_once(item, arm, sampled_pin, "sampled", seed)
                    fresh.append(r)
                    print(f"  {r['run_id']:<34} {r['outcome']:<9} {r.get('answer', '')[:42]!r}")

    runs = merge(previous, fresh)
    changed = regrade(runs, all_traps)
    if changed:
        print(f"  ({changed} stored runs re-graded by the current grader)")

    TRAPS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "task": "M1-5",
        "recorded_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pin": dataclasses.asdict(pin),
        "pin_fingerprint": pin.fingerprint(),
        "sampled_temperature": sampled_temp,
        "sampled_runs": args.runs,
        "hits_required": HITS_REQUIRED,
        "seed_offsets": list(SEED_OFFSETS[: args.runs]),
        "runs": runs,
    }
    RUNS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    print(f"\nraw -> {RUNS_PATH}  ({len(runs)} runs)")

    with_evidence = [i for i in all_traps if any(r["item"] == i["id"] for r in runs)]
    write_log(payload, with_evidence)
    print(f"log -> {LOG_PATH}")

    earned = [i["id"] for i in with_evidence if earned_arms(runs, i["id"])]
    print(f"\nEARNED ({len(earned)}/{THRESHOLD_TRAPS} required): {', '.join(earned) or 'none'}")
    return 0 if len(earned) >= THRESHOLD_TRAPS else 1


def write_log(payload: dict[str, Any], traps: list[dict[str, Any]]) -> None:
    runs = payload["runs"]
    pools = {
        "items": "Declared in M1-4, still claiming `is_trap` in the L1 bank",
        "retired": "Declared in M1-4, **claim withdrawn by ADR-005** — the bank items "
        "remain, as plain items",
        "candidates": "Authored in M1-5, never in the bank",
    }
    out: list[str] = []
    w = out.append
    w("<!-- Generated by spikes/m1_5_trap_reproduction.py (M1-5). Re-run with `make traps`.")
    w("     Raw runs, including the full text of every chain, are in runs.json. -->")
    w("")
    w("# Trap reproduction log — M1-5")
    w("")
    w(
        f"**Recorded** {payload['recorded_utc']} · **pin** `{payload['pin_fingerprint']}` "
        f"(`{payload['pin']['model']}` @ `{payload['pin']['digest'][:12]}`) · "
        f"**{len(runs)} runs**"
    )
    w("")
    w(
        "A trap is *declared* in M1-4 and **earned here**. An item tagged `is_trap: true` "
        "that does not reproduce its declared wrong chain is a normal item with a "
        "misleading tag."
    )
    w("")
    # The verdict belongs at the top. A log whose conclusion has to be assembled from a
    # results table is a log that gets read as "some numbers were measured".
    earned_all = [i["id"] for i in traps if earned_arms(runs, i["id"])]
    by_outcome = {o: sum(1 for r in runs if r["outcome"] == o) for o in OUTCOMES}
    w("## Verdict — the DoD is not met")
    w("")
    w(
        f"**{len(earned_all)} of {len(traps)} candidates earned their tag, against a floor "
        f"of {THRESHOLD_TRAPS}.** {by_outcome['correct']} of {len(runs)} runs were correct; "
        f"{by_outcome['trap']} reproduced a declared wrong chain."
    )
    w("")
    w(
        "The plan's stop rule was followed rather than the threshold lowered: twelve "
        "further candidates were authored across two rounds, the second abandoning "
        "word-problem arithmetic for inclusion-exclusion, constrained combinatorics and "
        "compounding. The finding survived it. **There is no shallow regime on this model "
        "to trap** -- ADR-004 established that thinking cannot be switched off and `low` "
        "is the floor, and at `low` the chain is still good enough to solve every "
        "misdirection we could construct."
    )
    w("")
    w(
        "What the arms *can* be separated by is **difficulty**, which is already verified "
        "on real runs: arm 1 wrong at 144 reasoning tokens where arm 2 is right at 1453, "
        "and `mb-01` correct on both at 5 vs 21. See "
        "[ADR-005](../../docs/decisions/ADR-005-traps-do-not-reproduce.md) for the four "
        "options and the recommendation; the decision is not the implementer's."
    )
    w("")
    w("## The two regimes, and why there are two")
    w("")
    w(
        f'M1-5\'s DoD is "≥ {payload["hits_required"]} of {payload["sampled_runs"]} runs". '
        "At the committed pin that count cannot exist: `GEN_TEMPERATURE=0` with a fixed "
        "`GEN_SEED` is greedy decoding, and two thinking-arm runs of `mb-13` came back "
        "byte-identical (259 reasoning tokens each) before this harness was written. Five "
        "runs there are one run five times, and the hit count can only be 0 or 5."
    )
    w("")
    w("| Regime | Settings | Question it answers |")
    w("| --- | --- | --- |")
    w(
        f"| **pinned** | the committed pin — `temperature=0`, `seed={payload['pin']['seed']}` "
        "| Does the trap fire **in the configuration the demo runs in**? Binary, and "
        "byte-stable, so one run is the honest form of five. |"
    )
    w(
        f"| **sampled** | `temperature={payload['sampled_temperature']:g}`, seeds "
        f"`{payload['pin']['seed']}+{payload['seed_offsets']}` | **How fragile is that "
        "binary?** The DoD's denominator is measured here, because this is the only "
        "regime where it means anything. |"
    )
    w("")
    w(
        "**A trap is earned when it fires pinned *and* reaches the threshold sampled, on "
        "the same arm.** Pinned alone is one point in sampling space with nothing to say "
        "how close the edge is; sampled alone does not describe the demo."
    )
    w("")
    w(
        "Outcomes are `correct`, `trap` (the declared wrong answer), `unparsed` (the answer "
        "could not be read without guessing which number in a worked line was meant) and "
        "`other` (wrong, but not in the way the trap intended). `unparsed` is kept separate "
        "on purpose: folding it into `other` would understate accuracy for free."
    )
    w("")
    w("## Results")
    w("")
    w("| Candidate | Pool | Arm | Pinned | Sampled trap | Correct | Other | Unparsed | Earned |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in traps:
        earned = earned_arms(runs, item["id"])
        for arm in sorted({r["arm"] for r in runs if r["item"] == item["id"]}):
            s_ = tally(runs, item["id"], arm, "sampled")
            pinned_run = next(
                (
                    r
                    for r in runs
                    if r["item"] == item["id"] and r["arm"] == arm and r["regime"] == "pinned"
                ),
                None,
            )
            pinned = (pinned_run or {}).get("outcome", "—")
            if pinned == "trap":
                pinned = "**TRAP**"
            w(
                f"| `{item['id']}` | {item['_pool']} | {arm} | {pinned} | "
                f"**{s_['trap']}/{s_['n']}** | {s_['correct']}/{s_['n']} | "
                f"{s_['other']}/{s_['n']} | {s_['unparsed']}/{s_['n']} | "
                f"{'✅' if arm in earned else '—'} |"
            )
    w("")
    for pool, label in pools.items():
        ids = [i["id"] for i in traps if i["_pool"] == pool]
        if ids:
            w(f"*{label}: {', '.join(f'`{i}`' for i in ids)}*")
    w("")
    w("## Per candidate")
    w("")
    for item in traps:
        earned = earned_arms(runs, item["id"])
        w(f"### `{item['id']}` — {', '.join(item['tags'])}{' · **EARNED**' if earned else ''}")
        w("")
        w(f"> {item['prompt']}")
        w("")
        w(
            f"**Correct answer** `{item['known_answer']}` · **intended wrong chain** "
            f"{', '.join(f'`{t}`' for t in item['trap_answers'])}"
        )
        w("")
        w(item["trap_note"])
        w("")
        for arm in sorted({r["arm"] for r in runs if r["item"] == item["id"]}):
            s_ = tally(runs, item["id"], arm, "sampled")
            pinned_run = next(
                (
                    r
                    for r in runs
                    if r["item"] == item["id"] and r["arm"] == arm and r["regime"] == "pinned"
                ),
                None,
            )
            pin_txt = (
                f"`{pinned_run['outcome']}` (answer `{pinned_run.get('answer', '')[:70]}`, "
                f"run `{pinned_run['run_id']}`)"
                if pinned_run
                else "not measured"
            )
            w(
                f"- **{arm}** — pinned: {pin_txt} · sampled: **{s_['trap']}/{s_['n']}** trap, "
                f"{s_['correct']}/{s_['n']} correct, {s_['other']}/{s_['n']} other, "
                f"{s_['unparsed']}/{s_['n']} unparsed"
            )
            hits = [
                r["run_id"]
                for r in runs
                if r["item"] == item["id"]
                and r["arm"] == arm
                and r["regime"] == "sampled"
                and r["outcome"] == "trap"
            ]
            if hits:
                w(f"  - reproducing runs: {', '.join(f'`{h}`' for h in hits)}")
        w("")
    LOG_PATH.write_text("\n".join(out) + "\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
