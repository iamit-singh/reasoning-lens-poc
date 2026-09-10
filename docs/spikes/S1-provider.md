# S1 — Provider thinking-trace fidelity

| | |
| --- | --- |
| **Task** | M1-1 · W1 · 1.5 h · **Gate G0** |
| **Status** | **Local arm run 10 Sep 2026 — PASS.** OpenAI arm still pending a key |
| **Decision doc** | [`../decisions/ADR-001-provider.md`](../decisions/ADR-001-provider.md) |
| **Harness** | `spikes/s1_reasoning_fidelity.py` · `make spike-s1` |

## The question, precisely

Does the API return **full, unsummarised** thinking text, and are `reasoning_tokens`
exposed in usage accounting?

## Method

One representative `multi_step` problem, run against each candidate provider tier with
thinking enabled. The probe problem lives in the harness rather than in the problem bank
because the bank (M1-4) does not exist until W2 and S1 must not wait for it. It is a
four-step arithmetic chain with a single checkable integer answer (18678), long enough to
force several reasoning steps and not memorisable as a stock puzzle.

Captured per candidate, verbatim, into `docs/spikes/S1-raw/`:

- the raw response,
- whether thinking text is complete or elided (including any withheld/redacted blocks),
- the usage block verbatim,
- whether the provider documents summarisation,
- the answer's correctness (a sanity check on the probe, not a measure of the provider).

## ⚠️ The trap this spike exists to avoid

**Do not let S1 quietly succeed.** The failure mode is running one prompt, seeing text
that looks like thinking, and moving on.

So the harness does not report "thinking text: present". It reports the **ratio** of
estimated tokens in the returned text to the provider's own `reasoning_tokens`, and G0
check 2 turns on that ratio, not on the presence of text. A large gap is the signature of
summarisation. The harness also refuses to probe a floating model alias, because a fidelity
finding attached to an alias expires silently.

## Findings

### Local generation — `gpt-oss:20b` · **PASS**

Run 10 Sep 2026 against the pin recorded by `make pin-local`
(`sha256:e7b273f963…`, MXFP4, ollama 0.33.3, temp 0, seed 20260910, effort medium).

| Measure | Value |
| --- | --- |
| Raw reasoning text present | **yes** |
| Where it arrives | a **`reasoning` field** on the message — *not* inline `<think>` tags |
| Reasoning text length | 2535 chars |
| Answer text length | 783 chars |
| Probe answer correct | **yes** (18678) |
| `usage.completion_tokens` | 1020 — **reasoning and answer combined** |
| `reasoning_tokens` in usage | **absent** |
| Wall clock | 32.5 s for 1183 tokens, cold load excluded |

**Verdict: full raw trace recovered, unelided.** There is no server withholding it, which
is the architectural reason ADR-001 moved generation local.

**Which field it is matters, and is the actionable half of this finding.** M1-8's segmenter
has to strip the trace consistently, and a `reasoning` field is a materially easier and
safer contract than scraping `<think>` tags out of prose — no delimiter to be emitted
mid-sentence, no ambiguity when the model mentions the tag. The segmenter should read the
field and treat inline tags as a fallback for other models, not the primary path.

### ⚠️ G0 check 2 is **not** satisfied by this run

ADR-001 claims local token counting is *"an improvement: this measurement gets more
accurate, not less"*, on the grounds that the trace can be counted with the model's own
tokenizer. **This run does not evidence that claim.** What it establishes is the weaker
half: the provider does not report `reasoning_tokens`.

`usage.completion_tokens` is a **combined** figure (1020 tokens for 3318 chars of reasoning
plus answer). Cost-of-thought needs reasoning tokens *separated* from answer tokens, and
nothing in the response provides that split. Two routes were checked and closed:

| Route | Result |
| --- | --- |
| `POST /api/tokenize` on the runtime | **404** — ollama 0.33.3 exposes no tokenize endpoint |
| `POST /api/embed` | **501** — server not started with `--embeddings`, and embeddings would not give a token count anyway |

Counting it exactly therefore needs a tokenizer dependency (`tiktoken` with the harmony
encoding, or the GGUF vocab read directly) — **not currently declared in
`analyzer/pyproject.toml`, and not budgeted by the plan.** Until that lands the check is
**unticked**, and any cost-of-thought number is an estimate from a chars-per-token ratio
(3.25 chars/token observed here), not a measurement.

### OpenAI analysis tier — not yet run

`--only openai` still needs a key, and `MODEL_ANALYZE` / `MODEL_ESCALATE` are unset. G0
check 5 (analyzer tier pinned to an exact dated id, never an alias) is therefore also open.
Per ADR-001, S1 must still run against OpenAI: the claim that it summarises thinking is a
strong expectation, not a measurement, and this project's thesis is that the difference
matters.

## What this changes downstream

| If | Then |
| --- | --- |
| G0 passes | `llm.py` (M1-6) is written against this provider; `MODEL_PIN` enters every cache key (C2.3) |
| Thinking is summarised | `trace_quality: "provider_summarised"` becomes a `ReasoningReport` field frozen at G1, and a permanent UI banner (FE-8) — the demo's central artifact is a summary and the reviewer hears it in W1 |
| No `reasoning_tokens` | B4 #7 is estimated, not measured; the calibration page carries the caveat |
| No candidate qualifies | Arm 2 becomes a hosted open-weight R1-class model (B6.5), decided in W1 |
