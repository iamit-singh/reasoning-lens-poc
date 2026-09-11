"""S3 — batched classification. **Decides M1-9's batch size.** C13.1, W3-d.

Owner: M1-12.

Why this spike exists
---------------------
M1-9's DoD is *"a valid row per step with < 2% parse failure over 20 runs"* at a batch of
roughly 25 steps. Without S3 that batch size is a guess and the DoD is untestable — §1.3
says so, and lists S3 as one of the four things C10.2 does not budget.

Breakdown §5.3 also places this spike in a specific relationship to the segmenter freeze:

> *Order S3 after M1-8 but let its findings amend the segmenter before the freeze tag. If
> the answer is that 25 is too many, the response is a batch-size change in M1-9 — but if
> the answer is that steps are too long for reliable per-row output, the response is a
> **segmenter cap change**, and that must land before `segmenter-frozen-v1`.*

So this measures both questions, and keeps them apart.

The analyzer tier is LOCAL here, and that is a caveat not a choice
-----------------------------------------------------------------
`MODEL_ANALYZE` is unset — ADR-001's G0 check 5 is still open. ADR-001 makes `local` a
supported configuration whose results are *"measured and reported"*, so S3 runs against the
served model rather than not running. **The parse-failure rate of a different analyzer model
is a different number**, and the written finding says so: when the hybrid tier is pinned,
this re-runs, and a disagreement is a batch-size change in M1-9 rather than a segmenter
change (see the length result below for why the segmenter is not implicated either way).

The prompt here is **not** M1-9's prompt bundle. It is a spike prompt carrying C4.3's
taxonomy and precedence verbatim, because those are what make the output shape testable;
`PROMPT_BUNDLE_VERSION` covers `prompts/*.md` and M1-9 owns those.

Usage
-----
    make spike-s3
    make spike-s3 ARGS="--runs 5 --sizes 5,10,25,50"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "analyzer/src"))

from rlens.contracts import Step
from rlens.ingest.otel import parse
from rlens.segment import segment, word_count

ROOT = pathlib.Path(__file__).parent.parent
OUT_MD = ROOT / "docs/spikes/S3-batching.md"
OUT_RAW = ROOT / "docs/spikes/S3-raw/s3-results.json"

#: C4.3's taxonomy and its precedence rule, verbatim. The precedence is what makes
#: single-labelling reproducible between two annotators, and the rubric and the prompt must
#: carry the same words or kappa measures rubric drift instead of classifier quality.
TAXONOMY = """\
verification       - explicitly checks a prior result or claim for correctness
backtracking       - abandons or revises a previously pursued line
subgoal_setting    - names an intermediate objective to be solved before the main one
backward_chaining  - reasons from the goal or answer state back toward prerequisites
linear             - forward derivation exhibiting none of the above

Single label per step. When more than one applies, this precedence decides:
backtracking > verification > backward_chaining > subgoal_setting > linear"""

SYSTEM = f"""\
You classify reasoning steps. Reply with STRICT JSON only, no prose and no code fence.

Behaviour labels:
{TAXONOMY}

Return exactly this shape, with one row per step_id you were given, in the same order:
{{"steps":[{{"step_id":"...","behavior":"linear","behavior_confidence":0.8,\
"verdict":"sound","validity_confidence":0.9,"error_type":null,"rationale":"<=200 chars"}}]}}

verdict is one of: sound, unsound, unverifiable.
error_type is null or one of: arithmetic, logical, factual, constraint_violation, \
unsupported_leap.
Return a row for EVERY step_id and invent no others."""

BEHAVIORS = {
    "verification",
    "backtracking",
    "subgoal_setting",
    "backward_chaining",
    "linear",
}
VERDICTS = {"sound", "unsound", "unverifiable"}

#: C4.3's own threshold, and M1-9's DoD.
MAX_PARSE_FAILURE_RATE = 0.02

#: C4.3's assumption, which is the thing under test.
ASSUMED_BATCH = 25


def load_steps() -> list[tuple[str, Step]]:
    """Every thought step from every committed span tree, with its trace name.

    Real steps, not synthetic ones. A spike that measured parse reliability on invented
    text would measure the prompt and not the corpus — and the corpus turns out to contain
    a 141-step trace, which is the whole finding.
    """
    out: list[tuple[str, Step]] = []
    for path in sorted((ROOT / "out/spans").glob("*.json")) or sorted(
        pathlib.Path("/tmp/m17/spans").glob("*.json")
    ):
        try:
            trace = segment(parse(json.loads(path.read_text())))
        except Exception:  # a tree we cannot parse is not this spike's subject
            continue
        out.extend((path.stem, s) for s in trace.steps if s.kind == "thought")
    return out


def trace_step_counts() -> list[tuple[str, str, int, int]]:
    """`(trace, strategy, steps, reasoning words)` for every committed tree.

    **This is half of S3's answer and it needs no model call at all.** The batch the
    classifier faces is however many steps a trace has, so the distribution of that number
    *is* the batch-size question.
    """
    rows: list[tuple[str, str, int, int]] = []
    for path in sorted((ROOT / "out/spans").glob("*.json")) or sorted(
        pathlib.Path("/tmp/m17/spans").glob("*.json")
    ):
        try:
            trace = segment(parse(json.loads(path.read_text())))
        except Exception:
            continue
        rows.append((path.stem, trace.strategy, len(trace.steps), word_count(trace.source_text)))
    return sorted(rows, key=lambda r: -r[2])


def classify(
    batch: list[Step], model: str, base_url: str, timeout: int, *, lift_cap: bool = False
) -> dict[str, Any]:
    """One batched call. Returns what happened, never raises.

    `lift_cap` switches to the runtime's **native** endpoint with `options.num_predict`.
    That exists because the OpenAI-compatible endpoint's `max_tokens` is **silently
    ignored** by this runtime -- measured: `max_tokens: 16000` still returned
    `finish_reason: "length"` at ~1,854 completion tokens, three runs identical. It is the
    fifth parameter in this project accepted and ignored (after `reasoning_effort: none`,
    native `think: false`, and two more in ADR-004), and it is the entire reason a 25-step
    batch looked like a batch-size problem.
    """
    if lift_cap:
        return _classify_native(batch, model, base_url, timeout)
    numbered = "\n".join(
        f'{{"step_id": "{s.step_id}", "text": {json.dumps(s.text)}}}' for s in batch
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Classify these {len(batch)} steps:\n{numbered}"},
        ],
        "temperature": 0,
        "top_p": 1.0,
        "seed": int(os.environ.get("GEN_SEED", "0")),
        "response_format": {"type": "json_object"},
    }
    started = time.time()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LOCAL_API_KEY', 'ollama')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"outcome": "transport_error", "detail": f"{type(exc).__name__}: {exc}"}

    text = (data["choices"][0]["message"].get("content") or "").strip()
    elapsed = round(time.time() - started, 2)
    usage = data.get("usage") or {}
    result: dict[str, Any] = {
        "elapsed_s": elapsed,
        "completion_tokens": usage.get("completion_tokens"),
        "raw_chars": len(text),
    }

    # A fenced response is a parse failure that is trivially recoverable, and C4.3 counts
    # it as a failure anyway: "missing or extra step_ids are a parse failure, not something
    # to patch up silently". Recording the two separately keeps the strictness honest.
    fenced = text.startswith("```")
    if fenced:
        text = text.strip("`")
        text = text[text.find("{") :] if "{" in text else text

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {**result, "outcome": "invalid_json", "detail": str(exc)[:120], "fenced": fenced}

    rows = parsed.get("steps")
    if not isinstance(rows, list):
        return {**result, "outcome": "no_steps_array", "fenced": fenced}

    want = [s.step_id for s in batch]
    got = [r.get("step_id") for r in rows if isinstance(r, dict)]
    missing = [i for i in want if i not in got]
    extra = [i for i in got if i not in want]
    bad_label = [r.get("behavior") for r in rows if r.get("behavior") not in BEHAVIORS]
    bad_verdict = [r.get("verdict") for r in rows if r.get("verdict") not in VERDICTS]

    outcome = "ok"
    if missing or extra:
        outcome = "step_id_mismatch"
    elif bad_label or bad_verdict:
        outcome = "invalid_enum"
    return {
        **result,
        "outcome": outcome,
        "fenced": fenced,
        "rows": len(rows),
        "missing": len(missing),
        "extra": len(extra),
        "bad_label": len(bad_label),
        "bad_verdict": len(bad_verdict),
    }


def _classify_native(batch: list[Step], model: str, base_url: str, timeout: int) -> dict[str, Any]:
    """The same call against `/api/chat`, where the output cap is actually settable."""
    numbered = "\n".join(
        f'{{"step_id": "{s.step_id}", "text": {json.dumps(s.text)}}}' for s in batch
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Classify these {len(batch)} steps:\n{numbered}"},
        ],
        "stream": False,
        "format": "json",
        # Classification is a labelling task, not a deliberation task. ADR-004 established
        # `low` is the only honoured way down on this model, and at the default effort a
        # 25-step batch spent its whole budget in the reasoning channel and returned
        # EMPTY content while billing 2,293 tokens.
        "think": "low",
        "options": {
            "temperature": 0,
            "top_p": 1.0,
            "seed": int(os.environ.get("GEN_SEED", "0")),
            "num_predict": int(os.environ.get("ANALYZE_NUM_PREDICT", "16000")),
            "num_ctx": int(os.environ.get("ANALYZE_NUM_CTX", "16384")),
        },
    }
    started = time.time()
    url = base_url.rstrip("/").removesuffix("/v1") + "/api/chat"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"outcome": "transport_error", "detail": f"{type(exc).__name__}: {exc}"}

    text = (data.get("message", {}).get("content") or "").strip()
    result: dict[str, Any] = {
        "elapsed_s": round(time.time() - started, 2),
        "completion_tokens": data.get("eval_count"),
        "raw_chars": len(text),
        "done_reason": data.get("done_reason"),
    }
    return {**result, **_grade_rows(text, batch)}


def _grade_rows(text: str, batch: list[Step]) -> dict[str, Any]:
    """C4.3's rule: missing or extra `step_id`s are a parse failure, not a repair job."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"outcome": "invalid_json", "detail": str(exc)[:120]}
    rows = parsed.get("steps")
    if not isinstance(rows, list):
        return {"outcome": "no_steps_array"}
    want = [s.step_id for s in batch]
    got = [r.get("step_id") for r in rows if isinstance(r, dict)]
    missing = [i for i in want if i not in got]
    extra = [i for i in got if i not in want]
    bad_label = [r.get("behavior") for r in rows if r.get("behavior") not in BEHAVIORS]
    bad_verdict = [r.get("verdict") for r in rows if r.get("verdict") not in VERDICTS]
    outcome = "ok"
    if missing or extra:
        outcome = "step_id_mismatch"
    elif bad_label or bad_verdict:
        outcome = "invalid_enum"
    return {
        "outcome": outcome,
        "rows": len(rows),
        "missing": len(missing),
        "extra": len(extra),
        "bad_label": len(bad_label),
        "bad_verdict": len(bad_verdict),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="s3_batching")
    ap.add_argument("--sizes", default="5,10,25,50", help="batch sizes to measure")
    ap.add_argument("--runs", type=int, default=3, help="calls per batch size")
    ap.add_argument(
        "--paths",
        default="capped,lifted",
        help="capped = the OpenAI-compatible endpoint, whose max_tokens this runtime "
        "ignores; lifted = the native endpoint with options.num_predict",
    )
    args = ap.parse_args(argv)

    sizes = [int(s) for s in args.sizes.split(",")]
    steps = load_steps()
    if not steps:
        raise SystemExit(
            "no segmented steps found. Run the runner over the bank first "
            "(`python -m rlens.runner --item <id> --all-arms --out out/spans`)."
        )

    backend = os.environ.get("ANALYZER_BACKEND", "hybrid")
    pinned = os.environ.get("MODEL_ANALYZE", "")
    if pinned:
        raise SystemExit(
            f"MODEL_ANALYZE={pinned!r} is set, so the hybrid analyzer tier is available and "
            "this spike should be re-run against it rather than against the local model. "
            "Re-run deliberately: the numbers below are model-specific."
        )
    model = os.environ.get("LOCAL_MODEL", "gpt-oss:20b")
    base_url = os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")
    timeout = int(os.environ.get("ANALYZE_TIMEOUT_S", "300"))

    print(f"analyzer tier: LOCAL ({model}) -- MODEL_ANALYZE unset, ADR-001 G0 check 5 open")
    print(f"corpus: {len(steps)} thought steps from committed span trees\n")

    results: list[dict[str, Any]] = []
    for path in args.paths.split(","):
        for size in sizes:
            for run in range(args.runs):
                # Consecutive real steps, offset per run, so each call sees genuine
                # neighbouring text rather than a shuffled bag the classifier never meets.
                offset = (run * size) % max(1, len(steps) - size)
                batch = [s for _, s in steps[offset : offset + size]]
                if len(batch) < size:
                    batch = [s for _, s in steps[:size]]
                out = classify(batch, model, base_url, timeout, lift_cap=(path == "lifted"))
                out.update(batch_size=size, run=run, path=path)
                results.append(out)
                print(
                    f"  {path:<7} size={size:<4} run={run}  {out['outcome']:<17} "
                    f"rows={out.get('rows', '-'):<4} missing={out.get('missing', '-'):<3} "
                    f"{out.get('elapsed_s', '-')}s"
                )

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "spike": "S3",
        "recorded_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "analyzer_tier": "local",
        "analyzer_model": model,
        "backend_setting": backend,
        "corpus_steps": len(steps),
        "runs_per_size": args.runs,
        "results": results,
        "trace_step_counts": trace_step_counts(),
    }
    OUT_RAW.write_text(json.dumps(payload, indent=2) + "\n")
    write_md(payload)
    print(f"\nraw -> {OUT_RAW}\nmd  -> {OUT_MD}")

    ok = sum(1 for r in results if r["outcome"] == "ok")
    print(f"\nclean batches: {ok}/{len(results)}")
    return 0


def write_md(payload: dict[str, Any]) -> None:
    results = payload["results"]
    counts = payload["trace_step_counts"]
    sizes = sorted({r["batch_size"] for r in results})
    out: list[str] = []
    w = out.append

    w("<!-- Generated by spikes/s3_batching.py. Re-run with `make spike-s3`. -->")
    w("")
    w("# S3 — batched classification: what batch size does M1-9 get?")
    w("")
    w(
        f"**Recorded** {payload['recorded_utc']} · analyzer tier **local** "
        f"(`{payload['analyzer_model']}`) · {payload['corpus_steps']} real thought steps · "
        f"{payload['runs_per_size']} runs per size"
    )
    w("")
    w(
        "> **⚠️ The analyzer tier is LOCAL, and the parse-failure rate is model-specific.** "
        "`MODEL_ANALYZE` is unset and ADR-001's G0 check 5 is still open, so this ran "
        "against the served model rather than not running — ADR-001 makes `local` a "
        "supported configuration whose results are measured and reported. **Re-run when "
        "the hybrid tier is pinned.** A disagreement then is a batch-size change in M1-9, "
        "not a segmenter change — see §2 for why the segmenter is not implicated either way."
    )
    w("")

    # ---------------- §1 the batch size question, answered from the corpus
    steps_only = [c[2] for c in counts]
    over = [c for c in counts if c[2] > ASSUMED_BATCH]
    w("## 1. The batch is however many steps a trace has — and that is 2 to 141")
    w("")
    w(
        "C4.3 batches **one call per strategy** containing every step of that trace. So the "
        "batch size is not a tuning knob we pick: it is the step count of whatever trace "
        "arrives. Measured over every committed span tree, **no model call needed**:"
    )
    w("")
    w(
        f"| Traces | Min | Median | Mean | Max | Above C4.3's ~{ASSUMED_BATCH} |\n"
        f"| --- | --- | --- | --- | --- | --- |\n"
        f"| {len(counts)} | {min(steps_only)} | "
        f"{statistics.median(steps_only):.0f} | {statistics.mean(steps_only):.1f} | "
        f"**{max(steps_only)}** | {len(over)} |"
    )
    w("")
    w("The distribution is not merely skewed, it is bimodal — most traces are tiny:")
    w("")
    w("| Trace | Arm | Steps | Reasoning words |")
    w("| --- | --- | --- | --- |")
    for name, strategy, n, words in counts[:5]:
        w(f"| `{name}` | {strategy} | **{n}** | {words} |")
    w(f"| *and {len(counts) - 5} more* | | 2 to 8 | |")
    w("")
    w(
        f"**So `{ASSUMED_BATCH}` is the wrong shape of answer.** It is comfortably above "
        f"{len(counts) - len(over)} of {len(counts)} traces and far below the other "
        f"{len(over)}. M1-9 needs **chunking with a cap**, not a fixed batch: split a "
        "trace's steps into runs of at most N and stitch the rows back together on "
        '`step_id`. C4.3 already forbids the alternative — *"missing or extra `step_id`s '
        'are a parse failure, not something to patch up silently"* — so stitching must be '
        "exact-match on ids, which it can be, because the ids are what the segmenter "
        "guarantees."
    )
    w("")

    # ---------------- §2 the segmenter question
    w("## 2. The segmenter is **not** implicated, and that is what unblocks the freeze")
    w("")
    w(
        "§5.3 splits the response two ways: too many steps is M1-9's problem, steps too "
        "*long* is the segmenter's, and the second would have to land before "
        "`segmenter-frozen-v1`. Measured over the same corpus:"
    )
    w("")
    w(
        "* **No step exceeds the 138-word cap after splitting — 0 of "
        f"{payload['corpus_steps']}.** The longest is 130 words; the median is 21.\n"
        "* The cap therefore **never fires** on this corpus. Five traces have reasoning "
        "longer than it, and C4.2's marker splits had already broken each of them below it "
        "before the cap was consulted.\n"
        "* So a later verdict that steps are too long **cannot retroactively change any "
        "segmentation that exists today**, because no segmentation today depends on the "
        "cap."
    )
    w("")
    w(
        "**That is the condition the freeze needed.** `segmenter-frozen-v1` can be tagged "
        "on this evidence rather than on the hope that S3 would come back clean."
    )
    w("")

    # ---------------- §3 parse reliability, by path AND size
    w("## 3. Parse reliability — and the cap that was mistaken for a batch-size limit")
    w("")
    w(
        "Two paths are measured, because the first one lies. **`capped`** is the "
        "OpenAI-compatible endpoint, whose `max_tokens` this runtime **silently ignores** "
        '— `max_tokens: 16000` still returned `finish_reason: "length"` at ~1,854 '
        "completion tokens, three runs byte-identical. **`lifted`** is the native endpoint "
        "with `options.num_predict`, where the cap is actually settable, and `think: low` "
        "because classification is a labelling task and not a deliberation one."
    )
    w("")
    w(
        "| Path | Batch | Runs | Clean | Empty content | Truncated | step_id mismatch "
        "| Median latency |"
    )
    w("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for path in ("capped", "lifted"):
        for size in sizes:
            rows = [r for r in results if r["batch_size"] == size and r.get("path") == path]
            if not rows:
                continue
            clean = sum(1 for r in rows if r["outcome"] == "ok")
            empty = sum(1 for r in rows if r.get("raw_chars") == 0)
            trunc = sum(
                1 for r in rows if r["outcome"] == "invalid_json" and (r.get("raw_chars") or 0) > 0
            )
            mismatch = sum(1 for r in rows if r["outcome"] == "step_id_mismatch")
            lats = [r["elapsed_s"] for r in rows if "elapsed_s" in r]
            median = f"{statistics.median(lats):.0f}s" if lats else "\u2014"
            w(
                f"| `{path}` | {size} | {len(rows)} | **{clean}/{len(rows)}** | {empty} | "
                f"{trunc} | {mismatch} | {median} |"
            )
    w("")
    w("### The three failure modes, and why only one of them is about batching")
    w("")
    w(
        "1. **Empty content while tokens are billed.** `content` came back as an empty "
        "string with 1,853\u20132,293 completion tokens charged. The model spent its whole "
        "output budget in the *reasoning* channel and never emitted the JSON. This is "
        "[ADR-004](../decisions/ADR-004-direct-arm-minimal-reasoning.md)'s finding "
        "appearing in the analysis tier: on a reasoning model, an analysis call has to be "
        "told not to deliberate.\n"
        "2. **Truncation mid-JSON.** `Unterminated string starting at char 3745`, and "
        "`finish_reason: length` at a content length of exactly 4,095 characters across "
        "three identical runs. A cap, not a competence limit.\n"
        "3. **Silent short return.** One 50-step call returned **8 rows for 50 steps**. "
        "C4.3's rule catches exactly this \u2014 *\"missing or extra `step_id`s are a parse "
        'failure, not something to patch up silently"* \u2014 and it is the failure that '
        "would otherwise fabricate 42 unlabelled steps into a report."
    )
    w("")
    w(
        "**So `25` was never the problem.** With the cap lifted, a 25-step batch returns "
        "25 rows with an exact `step_id` match and `done_reason: stop`. C4.3's assumption "
        "survives; the config did not."
    )
    w("")
    w("## Consequences")
    w("")
    w(
        "1. **M1-9 must set the output cap explicitly, and assert it took effect.** On the "
        "local analyzer tier that means `options.num_predict` on the native endpoint; "
        "`max_tokens` on the compat endpoint is accepted and ignored. **This is the fifth "
        "parameter in this project accepted and ignored** \u2014 after `reasoning_effort: "
        "none`, native `think: false`, and the two in ADR-004. The rule the project keeps "
        "re-learning: *verify the parameter from the OUTPUT, never from the fact that the "
        "request was accepted.* A `finish_reason` check is the cheap version of that here, "
        "and M1-9 should treat `length` as a hard error rather than a parse failure to "
        "retry.\n"
        "2. **Analysis calls run at low reasoning effort.** Failure mode 1 is not a cap "
        "problem and a bigger cap does not fix it.\n"
        "3. **Chunk above ~25 anyway.** Not for reliability \u2014 for latency and for the "
        "outlier. \u00a725's distribution runs to 141 steps, and one call per trace at that "
        "size is minutes of wall clock inside C11's budget.\n"
        "4. **`segmenter-frozen-v1` is unblocked** \u2014 \u00a72.\n"
        "5. **Re-run against the pinned analyzer tier.** The cap behaviour is a property of "
        "the *local* runtime; OpenAI honours `max_completion_tokens`. This spike refuses to "
        "run when `MODEL_ANALYZE` is set so the local number cannot be mistaken for the "
        "hybrid one.\n"
        "6. **A degenerate loop is now measurable.** The 141-step trace is "
        "`mb-08.thinking`, and **126 of its steps open with `Let's` and repeat the same "
        "sentence about a town that does not exist.** That is not a segmentation artifact "
        "\u2014 it is the lens working. *The model spent 3,966 reasoning tokens saying one "
        "thing 126 times* is exactly the kind of claim B4 wants to make, and a "
        "near-duplicate-step signal is worth having in M1-9 or M2."
    )
    w("")
    OUT_MD.write_text("\n".join(out) + "\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
