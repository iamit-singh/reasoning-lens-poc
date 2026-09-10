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

### G0 check 2 — **satisfied by a local count**, not by the provider

The runtime reports no `reasoning_tokens`, and `usage.completion_tokens` (1020) bundles
reasoning **with** the answer. Two cheap routes to a split were checked and closed:

| Route | Result |
| --- | --- |
| `POST /api/tokenize` on the runtime | **404** — ollama 0.33.3 exposes no tokenize endpoint |
| `POST /api/embed` | **501** — and embeddings would not give a token count anyway |

So the split is counted locally with the model's own encoding — `o200k_harmony`, which is
gpt-oss's actual tokenizer. `tiktoken>=0.9` is now a declared analyzer dependency and
`make spike-s1` reports the count on every run:

| Measure | Value |
| --- | --- |
| Tokenizer | `o200k_harmony` |
| **Reasoning tokens (exact)** | **741** |
| Answer tokens (exact) | 269 |
| Counted total | 1010 |
| Runtime's `completion_tokens` | 1020 |
| **Structural residual** | **+10** |
| **Reasoning share of output** | **73.4%** |
| chars/token, reasoning only | 3.42 |

**The +10 residual is the check on the check, and it is why this counts as evidence.** The
harmony format wraps each channel in structural tokens (`<|channel|>analysis<|message|>` and
friends) that the runtime bills and the extracted text does not contain, so a small positive
residual is expected. A large residual, or a negative one, would mean the encoding is wrong
for this model — which is exactly the failure that a lone plausible-looking number would
hide. At 1.0% of output, the account reconciles.

> **The tokenizer is therefore part of the pin, not a default.** `LOCAL_TOKENIZER` travels
> with `LOCAL_MODEL`. Counting one model's text with another model's encoding produces a
> plausible **wrong** number — the worst kind of measurement error, because nothing looks
> broken. The approved fallback `qwen3:14b` does **not** use harmony, so a model swap
> without a tokenizer swap would silently corrupt every cost-of-thought figure. The spike
> refuses to guess: an unrecognised model reports *no count* rather than a default.

**This is the measurement ADR-001 predicted would improve.** A provider's
`reasoning_tokens`, where offered at all, is a number you must trust. This one is
recomputable from committed text with a pinned encoding, and it reconciles against the
runtime's own billing to within the structural overhead.

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
| No `reasoning_tokens` | ~~B4 #7 is estimated~~ — **resolved**: counted exactly with `o200k_harmony` (741 for the probe, 73.4% of output). No caveat needed; the tokenizer is pinned |
| No candidate qualifies | Arm 2 becomes a hosted open-weight R1-class model (B6.5), decided in W1 |
