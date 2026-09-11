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

| # | Check | Pass condition | Result — 10 Sep 2026 |
| - | --- | --- | --- |
| 1 | Full raw reasoning text returned | present and complete; no elision | ✅ **PASS** — 2535 chars in a `reasoning` field (not inline `<think>` tags), unelided, answer correct. [S1](../spikes/S1-provider.md) |
| 2 | Reasoning tokens countable | exactly, with the model's own tokenizer — **an improvement: this measurement gets more accurate, not less** | ✅ **PASS** — the runtime reports none, so counted locally with `o200k_harmony`: **741 reasoning tokens, 73.4% of output**, reconciling to the runtime's billed 1020 within a +10 structural residual. [S1](../spikes/S1-provider.md) |
| 3 | **Tool contract held** | calculator + lookup called correctly and repeatably — gates arm 3, must pass **before** W3 | ✅ **PASS** — 20/20, 100% on all four scenarios incl. tool-choice and the false-positive check. [S6](../spikes/S6-tools.md) |
| 4 | Pin tuple recorded | every field above, reproducibly | ✅ **PASS** — recorded below and in `.env`; `make pin-local` reproduces it |
| 5 | Analyzer tier pinned separately | exact dated OpenAI id, never an alias | ✅ **PASS** — 11 Sep 2026 (W4). Key arrived; `MODEL_ANALYZE=gpt-5-mini-2025-08-07`, `MODEL_ESCALATE=gpt-5-2025-08-07`. Both verified live, see below |
| 6 | This ADR committed | ✅ | ✅ |

### The analysis pin, as run — closed 11 Sep 2026 (W4)

G0 check 5 was the one check this gate could not answer in W1, and it stayed open for
three weeks for a reason that was never technical: there was no key. One arrived, so the
check is closed on measurement rather than on intent.

```
MODEL_ANALYZE=gpt-5-mini-2025-08-07     # classifier + triage (C4.3)
MODEL_ESCALATE=gpt-5-2025-08-07         # escalation tier (M2-5)
ANALYZE_REASONING_EFFORT=low
ANALYZE_MAX_OUTPUT_TOKENS=16000
```

**Both ids were probed before being written down**, because an id that appears in the
model list is not the same as an id that answers:

| | `gpt-5-mini-2025-08-07` | `gpt-5-2025-08-07` |
| --- | --- | --- |
| `response_format: json_object` | ✅ strict JSON returned | ✅ |
| `reasoning_effort: low` | ✅ accepted, 64 reasoning tokens | ✅ accepted, 64 |
| `max_completion_tokens` | ✅ honoured, `finish_reason: stop` | ✅ honoured |
| Latency, trivial prompt | **3.8 s** | **19.9 s** |

**`MODEL_ESCALATE` is stronger, and the 5x latency is the reason the tiering exists.**
gpt-5 costs five times the wall clock of gpt-5-mini on an identical request. Running
every step through it would blow C11's analysis deadline; running *only escalated* steps
through it is affordable, which is why `ESCALATION_MAX_STEPS=8` is a cap and not a
suggestion. The tier is a real quality difference bought with a real cost, and both
halves are now measured rather than assumed.

> **The `reasoning_effort: low` row is the one that matters for M1-9.** S3 measured the
> local analyzer tier spending its entire output budget in the reasoning channel and
> returning empty `content`. OpenAI exposes the same dial, and the same setting. The
> parameter is honoured here — verified from the *output*, which is the only place this
> project accepts a parameter as honoured.

### What this does and does not change

**It does not re-open the generation decision.** Arm 2 still needs raw reasoning text and
OpenAI still does not return it; a key changes nothing about that, and moving generation
to OpenAI would delete the finding this PoC exists to make. All three arms stay local.

**It does change what S3's numbers mean.** [S3](../spikes/S3-batching.md) ran against the
*local* analyzer tier because this pin did not exist, and it said so in its own header and
in consequence 5: *re-run when the hybrid tier is pinned.* M1-9 measures its parse-failure
rate against this pin, and that measurement supersedes S3's for the purpose of M1-9's DoD.
S3's structural findings — chunk-and-stitch, assert the cap, `length` is a hard error —
are properties of the *task*, not of the runtime, and carry over unchanged.

### The generation pin, as run

`.env` is gitignored, so the pin is recorded here — a pin that exists only in an
uncommitted file is not reproducible evidence. Regenerate with `make pin-local`.

```
LOCAL_MODEL=gpt-oss:20b
LOCAL_MODEL_DIGEST=sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb
LOCAL_QUANTIZATION=MXFP4
LOCAL_RUNTIME="ollama 0.33.3"          # served natively, Metal
GEN_TEMPERATURE=0
GEN_TOP_P=1.0
GEN_SEED=20260910
LOCAL_REASONING_EFFORT=medium
LOCAL_TOKENIZER=o200k_harmony        # gpt-oss. qwen3 would need a different encoding
```

> **The digest is the weights-file sha256, not ollama's short id.** `ollama list` prints a
> 12-character truncated manifest id (`17052f91a42e`); `pin_local.sh` was recording that,
> which is exactly the weakness this ADR rejects hosted ids for. It now reads the full
> artifact digest from the modelfile's `FROM` line. The short id is kept as a convenience
> field and is **not** part of the pin.

### Check 2, closed — and the tokenizer joins the pin

The ADR asserted that counting reasoning tokens locally is an *improvement* on a provider's
number. That is now **evidenced rather than asserted**: `tiktoken>=0.9` is a declared
analyzer dependency, and `make spike-s1` counts the trace with `o200k_harmony` on every run.

The reconciliation is what makes it evidence. Counted reasoning (741) plus answer (269) is
1010 against the runtime's billed 1020 — a **+10 structural residual**, which is the harmony
channel wrapper the runtime bills and the extracted text does not contain. A large or
negative residual would mean the encoding is wrong for the model, so the residual is
reported on every run rather than discarded.

**`LOCAL_TOKENIZER` is now part of the pin tuple**, for the same reason the digest is:
counting one model's text with another model's encoding yields a plausible **wrong** number,
and nothing looks broken when it happens. The approved fallback `qwen3:14b` does not use
harmony. The spike therefore refuses to guess — an unrecognised model reports *no count*
rather than falling back to a default encoding.

## Consequences

- Hosted generation spend: **$130–150 → $0.** Analysis: a few dollars total. The spend
  breaker becomes vestigial (retained as a cheap guard, no longer a control).
- Latency stops being a gate. Local generation is slower per token; a reasoning-heavy problem
  may take 30–90 s per arm. The demo replays from cache, so this is a **footnote to measure
  and report**, not a launch gate.
- **New risk:** local tool-calling reliability. A W2 spike tests it before arm 3 is built.
