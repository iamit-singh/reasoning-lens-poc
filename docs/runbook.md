# Runbook

## Local development

```
make install PY=python3.12     # venv + analyzer[dev]
make ci                        # everything a PR runs -- no model, no key, no network
```

## The local generation model — first-time setup (M1-15, W2-0)

```
brew install ollama                    # or the app from ollama.com
ollama serve                           # keep running. Native, NEVER in Docker.
make models                            # ollama pull gpt-oss:20b   (~13 GB)
make pin-local                         # emits the pin tuple -> paste into .env
make spike-s1 ARGS="--only local"      # confirm raw reasoning actually arrives
make spike-s6                          # confirm tool calling. GATES ARM 3.
```

**Serve it natively, never in Docker.** Containerised inference on macOS loses Metal, and a
20B model on CPU is unusable. Compose reaches the host model at `host.docker.internal`.

**The pin is the deliverable, not the pull.** `make pin-local` exits non-zero if it cannot
discover a field, because a report built on an incomplete pin is not reproducible — better a
failed command than a number that cannot be defended.

**If it is too slow to iterate against**, switch to the approved fallback `qwen3:14b`
(~9 GB, roughly twice the speed). Update the pin tuple; nothing structural changes.

| Symptom | Response |
| --- | --- |
| Connection refused on :11434 | `ollama serve` is not running |
| Model too slow, or won't fit | `qwen3:14b`. **Never** a 32B model — 24 GB will not hold it plus the KV cache |
| No raw reasoning in the response | Check both shapes: a `reasoning`/`reasoning_content` field *and* inline `<think>` tags. Which one it is matters — the segmenter has to strip it consistently |
| No reasoning tokens in `usage` | Fine. Count locally with the model's own tokenizer: exact, and better than a provider's number |
| S6 below 90% on any scenario | Try `qwen3:14b`. Do **not** move arm 3 to OpenAI — that measures vendors, not strategies |

`MOCK_LLM=1` is the default in `docker-compose.yml` and in CI: local dev and CI are
**deterministic and cost-free** by construction (C7.1). Cassettes are recorded once per
prompt-bundle version by `make record-cassettes` (owner: M1-14).

```
docker compose up              # + redis, MOCK_LLM=1, DEMO_MODE=cached
```

## The every-PR job set (C7.2)

| Job | Command | Owner if it fails |
| --- | --- | --- |
| lint (ruff) | `make lint` | whoever pushed |
| lint (mypy, strict) | `make typecheck` | whoever pushed |
| lint (eslint) | `cd frontend && npm run lint` | whoever pushed |
| unit | `make unit` | whoever pushed |
| contract | `make contract` | **stop** — a data contract moved |
| integration-mock | `make integration-mock` | check cassettes are current for `PROMPT_BUNDLE_VERSION` |
| import-linter boundaries | `make boundaries` | **I1 escalation** — not an implementer-level decision |
| schema-freeze | `make schema-freeze` | **stop** — someone edited the held-out labels |
| prompt-bundle version | reported in CI | bump and re-record cassettes |

## The analysis tier (W4)

```
make report ARGS="--item mb-08"              # span trees -> a ReasoningReport
MOCK_LLM=1 make report ARGS="--all"          # the whole bank, offline, from cassettes
make classify-reliability ARGS="--runs 20"   # M1-9's DoD. COSTS SPEND
make record-cassettes                        # re-record after ANY prompt edit
```

`MODEL_ANALYZE` and `MODEL_ESCALATE` are exact dated ids and `versions.analyzer_pin()`
refuses an alias. Three settings exist only because S3 measured the failures they prevent:

| Setting | What it prevents |
| --- | --- |
| `ANALYZE_REASONING_EFFORT=low` | a classification call spending its whole output budget in the reasoning channel and returning **empty content** while billing for it |
| `ANALYZE_MAX_OUTPUT_TOKENS` | truncation mid-JSON. `finish_reason: length` is a **hard error**, not a parse failure to retry — retrying reproduces it exactly |
| `CLASSIFY_CHUNK_SIZE=25` | a 141-step trace in one call. It is a **cap**, not a batch size |

| Symptom | Response |
| --- | --- |
| `AnalysisTruncated` | Raise `ANALYZE_MAX_OUTPUT_TOKENS` or lower `CLASSIFY_CHUNK_SIZE`. Do **not** retry |
| `empty content with N completion tokens billed` | Lower `ANALYZE_REASONING_EFFORT`. A bigger cap does not fix this |
| `classifier_parse_failure` on an arm | The arm renders **unannotated**, deliberately. Levers in order: smaller chunk, tighter schema, shorter rationale cap. **Not** a lever: filling the missing row |
| `the call exceeded its Ns budget` | The wall-clock deadline fired. See below |
| `MOCK_LLM=1 still needs MODEL_ANALYZE` | Replay verifies the (model, prompt) pair a cassette recorded, so a replayed report's `judge_triage_pin` is true. It is a public id, not a secret |
| `cassette … recorded for a different request` | A prompt changed. `make record-cassettes` |

### The deadline is a wall clock, and it was not always

`ANALYSIS_DEADLINE_S` used to be passed to `urlopen(timeout=…)`, which bounds each socket
*operation*. M1-9 measured **a single call taking 969 seconds against a 110-second
deadline**: the block was inside the call, so nothing tripped. It is now enforced from
outside, and a call that overruns is abandoned rather than waited on.

**C11 budgets 18 s for classify+triage and this tier does not meet it.** Median per-trace
latency is ~9 s, but a 25-step chunk carrying 125 steps of context runs to ~100 s. That is
a known Month-3 conversation, not a surprise to have in Month 3.

## Labelling (M1-11)

```
make draw-sample                      # ONCE, before the first label. Refuses a redraw
make label ARGS="--annotator amit"    # two labels per step, one pass
make label ARGS="--status"            # how far through the queue
```

**Read [`calibration/rubric.md`](../calibration/rubric.md) first and keep it open.** The
tool is blind by construction — it cannot show a classifier prediction, and it withholds
the known answer and the rest of the trace.

| Symptom | Response |
| --- | --- |
| `no draw in calibration/sampling.json` | `make draw-sample`. The seed is committed **before** the first label (Hazard 2) |
| `a draw already exists` | Correct behaviour. A redraw after labelling begins re-labels every affected step |
| `N drawn steps are not in the corpus` | **Stop.** The segmenter moved under the draw — Hazard 1 firing. Resolve the freeze before labelling anything |
| `check-rubric-drift: FAIL` | The rubric and the classifier prompt disagree. Edit both or neither: κ would otherwise measure the wording |

## `DEMO_MODE=cached` — now the demo-safety switch

It was a spend control. Generation is local and free, so its job changed: it guarantees a
**zero-dependency run** when the network, the key or the model is unavailable. That makes it
more useful than before, not less — a local demo has more single points of failure than a
hosted one, not fewer.

Run the demo with `make demo`. The spend guard survives at a token $5/$10, purely against a
runaway loop.

## Version discipline

The cache key covers the item, the strategy, the runner version, the **generation pin
fingerprint**, the **analyzer pin**, the analyzer version, the prompt bundle version, and the
backend choice (`hybrid` / `local`).

The generation pin is a **tuple**, not an id — model, file digest, quantization, runtime,
temperature, top_p, seed, reasoning effort. An id alone does not reproduce a local number:
the same tag can be re-pulled as different weights, and sampling settings change the output.
Each field invalidates the cache on its own, and there is a test asserting exactly that.

`hybrid` and `local` never share cache entries — they are different analyzers, and both are
reported side by side.

**A change to the generation pin also requires re-running calibration and the faithfulness
batch job** — agreement and hint-verbalisation rates are model-specific.

`rlens.versions.analyzer_pin()` refuses to be absent *and* refuses a floating alias: a number
pinned to an alias expires silently.

## The six operating procedures (M3-5a)

**Every procedure below was executed once before it was written down.** That is M3-5a's DoD
and it is not ceremony: a runbook written from the source is a description of what the
author believes the commands do, and the gap between that and what they *do* is exactly the
gap an operator discovers at the worst moment. Each entry names what it produced when it
was run, so a reader can tell whether their run matched.

### P1 — Bring the demo up

```
make fe-build          # static export -> frontend/out
make serve-api         # localhost:8000, cache-first, DEMO_MODE from .env
```

`/readyz` is the check that matters, not `/healthz`. It reports `cached_reports`,
`stale_reports` and the breaker state. **A green `/healthz` with an empty cache is a demo
with nothing to show**, which is why readiness reports what it is ready *for*.

### P2 — Prove the demo works before an audience sees it

```
make smoke
```

Starts a real server **with `OPENAI_API_KEY` stripped**, runs 16 checks, stops it. *We did
not call the provider* and *we could not call the provider* are different claims, and only
the second proves the fallback product.

> **Observed on first run:** 4 of 16 failed, and every failure was real — two stale
> reports, a thin cache, and a breaker pointed at a directory. Do not treat a red smoke run
> as flaky. It has not yet produced a false alarm.

### P3 — Trip the spend breaker, and reset it

```
make trip-breaker      # writes a real over-limit total; the live route now 503s
make reset-breaker     # clears it
```

The trip goes through the **same code path** the real limit takes rather than simulating
it. Note the fail-closed rule: a *missing* spend file is $0 spent and allowed; an
*unreadable* one is denied. If live runs are refused with `spend file unreadable`, the file
is corrupt or `SPEND_FILE` points somewhere wrong — that is the breaker working.

### P4 — Re-warm the cache after any pin change

```
make report            # span trees -> out/reports, one report per item
```

**Required after any change to the runner version, analyzer version, prompt bundle or
generation pin.** The server refuses to start on a stale cache rather than serving it,
because a report built before any of those moved is a set of numbers attributed to a system
that is no longer running. `CACHE_STRICT=0` overrides, and choosing it is a decision to
publish exactly that.

### P5 — Rebuild the published measurements

```
make faithfulness      # faithfulness/panel.json from S4's records — no model, no network
make calibrate         # calibration/results/latest.json (dev set; safe, the default)
make calibrate ARGS="--iaa"   # + B4 #1, the human-vs-human kappa on the double labels
make seeded-errors     # judge recall; COSTS SPEND
```

`make faithfulness-check` and the calibration-page grep both run in CI, so a committed
panel cannot drift from the records behind it and no page can render a number its source
file does not contain.

### P6 — Hand the analyzer to someone else

```
make wheel
```

Builds the wheel, installs it into a venv with nothing else in it **outside the repo**, and
ingests a third-party LangGraph capture. This is the real handover artifact.

> **Observed on first run:** it failed. The JSON Schema was not packaged, so `load_schema()`
> raised in any fresh install while the whole test suite stayed green from the source
> checkout. **Run this after touching `analyzer/`, not before a release.**

---

## Deploy

**There is none.** The demo runs from a laptop ([ADR-003](decisions/ADR-003-hosting.md)): no
domain, no registry, no cloud service, no rollback, no rate limiting, no iframe embed.

What survives: `make smoke` against `localhost` as the acceptance script, a clean-venv
install proof plus the analyzer wheel as the real handover artifact, and a fallback video —
because one laptop is a single point of failure and pretending otherwise is how demos die.
