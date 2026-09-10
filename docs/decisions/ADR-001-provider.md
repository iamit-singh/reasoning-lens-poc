# ADR-001 — A hybrid runtime: the local model generates, OpenAI analyses

| | |
| --- | --- |
| **Status** | **Accepted** — 10 Sep 2026 (W1) |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | Plan §C2.3, §C4.3, §C4.4, §C8, Appendix D #2 · see [plan amendment 001](../../../plan-amendment-001-local-hybrid.md) |
| **Gate** | **G0**, re-scoped by this ADR (§Gate below) |

## Context

The plan assumed a frontier hosted provider would serve all three arms, and asked S1 to
find which one returns full, unsummarised thinking text. Two facts changed the question:

1. **Only an OpenAI key is available.** No Anthropic access.
2. **OpenAI's reasoning models do not return raw thinking.** They return a summary plus a
   reasoning-token count; the chain stays server-side.

Arm 2 exists to show a model's *own native thinking*. Built on OpenAI it would show a
summary of thinking — a different artifact supporting a weaker claim, caveated on every
screen. The plan pre-decided this branch (fall back to an open-weight R1-class model for
arm 2); this ADR takes it, and further: **the fallback becomes primary, and runs locally.**

## Decision

**Generation is local. Analysis is OpenAI. Local-only is a supported configuration.**

| | Generation | Analysis |
| --- | --- | --- |
| What | all three arms — the reasoning traces that are the object of study | classify each step, flag unsound steps, whole-trace consistency |
| Volume | high; traces are long | low; short texts in, structured rows out |
| Hard requirement | **raw reasoning text must be recoverable** | **< 2% malformed responses over ~25-item batches** |
| Runs on | **`gpt-oss:20b`, local** | **OpenAI** |

Three reasons, in descending weight:

1. **Raw traces by construction** — there is no server to withhold them.
2. **A stronger examiner than the subject** — the escalation tier only means something if
   the escalated verdict comes from a better model than the first pass. One local model for
   every tier deletes that mechanism while keeping its name in the report.
3. **Separation of subject and examiner — an improvement on the original plan.** One model
   both producing and judging its own reasoning is self-evaluation, and it is the first
   thing a reviewer attacks. The plan had that weakness; this split removes it.

### All three arms run on the same model — non-negotiable

The arms compare reasoning **strategies**. Different models per arm would measure vendors
instead, and the finding evaporates. This was implicit when one provider served all three;
a hybrid runtime makes it easy to violate by accident, so it is stated explicitly.

> **In particular: do not move arm 3 to OpenAI because its tool calling is better.** That
> trade is not available. If no local model can hold the tool contract, the correct response
> is a two-arm comparison, stated plainly.

## Model choice

Hardware: **Apple M4 Pro, 24 GB unified memory** — about 13–14 GB of weights once the OS,
KV cache and toolchain are accounted for. Nothing at 32B fits.

| Candidate | Size | Raw reasoning | Tool calling | Verdict |
| --- | --- | --- | --- | --- |
| **`gpt-oss:20b`** | ~13 GB | ✅ full CoT | ✅ | **Chosen.** Reasoning-effort dial is directly useful for cost-of-thought; OpenAI's own open weights sharpen the story — same lineage as the API, one hides its reasoning, one shows it |
| `qwen3:14b` | ~9 GB | ✅ switchable | ✅ | **Approved fallback** if 20B is too slow to iterate against |
| `deepseek-r1:14b` | ~9 GB | ✅ | ❌ weak | **Rejected** — see below |
| `qwq:32b` | ~19 GB | ✅ | ✅ | **Rejected** — does not fit |

> **Why the R1 distill is rejected despite being the model the plan names.** The distills
> reason well and fumble the function-call format. Arm 3 must call a calculator and a lookup
> tool, and the same-model rule forbids compensating by moving the arm. The failure would
> surface in W3 *after* the arm was built, with no cheap repair.

## `MODEL_PIN` is redefined

An id does not reproduce a local number. The pin is now a tuple, and all of it travels with
every report and enters the cache key:

```
model file digest (the exact GGUF/MLX artifact)
quantization
sampling params — temperature, top_p, seed
runtime + version (e.g. ollama 0.x)
reasoning-effort setting, where exposed
```

This is **stricter** than the hosted pin it replaces: a hosted endpoint can change under a
fixed id; a file digest cannot. The analyzer's own pin (the OpenAI model doing the
classification) is recorded separately, because the two move independently.

## Local-only as a measured configuration

The analyzer's model is a config choice: **hybrid** (default) or **local-only**. Human labels
are fixed ground truth, so scoring a second classifier against them is nearly free — the
calibration harness runs both and reports both.

"Can this run entirely on a laptop with no API access?" becomes a published number rather
than an assumption. It also derisks the demo: if the key fails on the day, local-only is a
known quantity with known numbers, not an untested fallback.

## Gate G0, re-scoped

The original question ("does the provider return unsummarised thinking?") is answered by
architecture. The gate now asks three things of the **local** model:

| # | Check | Pass condition |
| - | --- | --- |
| 1 | Full raw reasoning text returned | present and complete; no elision |
| 2 | Reasoning tokens countable | exactly, with the model's own tokenizer — **an improvement: this measurement gets more accurate, not less** |
| 3 | **Tool contract held** | calculator + lookup called correctly and repeatably — gates arm 3, must pass **before** W3 |
| 4 | Pin tuple recorded | every field above, reproducibly |
| 5 | Analyzer tier pinned separately | exact dated OpenAI id, never an alias |
| 6 | This ADR committed | ✅ |

**S1 must still run.** The claim about OpenAI's summarisation is a strong expectation, not a
measurement, and this project's thesis is that the difference matters. If OpenAI exposes more
than expected, that is a finding worth having — it does not reverse this ADR, because the
local model is now preferred on **reproducibility** grounds independent of fidelity.

## Consequences

- Hosted generation spend: **$130–150 → $0.** Analysis: a few dollars total. The spend
  breaker becomes vestigial (retained as a cheap guard, no longer a control).
- Latency stops being a gate. Local generation is slower per token; a reasoning-heavy problem
  may take 30–90 s per arm. The demo replays from cache, so this is a **footnote to measure
  and report**, not a launch gate.
- **New risk:** local tool-calling reliability. A W2 spike tests it before arm 3 is built.
