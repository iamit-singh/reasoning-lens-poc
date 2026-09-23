# Runbook

> **Every command below was re-run from a clean `git clone` on 18 Sep 2026** (M3-5c's cold
> run, [`runbook-cold-run.md`](runbook-cold-run.md)). Eight of them did not work as written.
> The corrections are folded in here; the record of what failed and why is in that file,
> because a runbook that quietly became correct teaches nobody what it was wrong about.

## Local development

```
make install                   # venv + analyzer[dev] + backend/requirements.txt
make ci                        # everything a PR runs -- no model, no key, no network
```

**`make install` then `make ci` is the contract**, and it now holds from an empty checkout
(~33 s). It did not until the cold run: `ci` runs `backend-tests`, which needs FastAPI,
which nothing installed — it was in the author's venv from an ad-hoc `pip install` recorded
nowhere, so the suite was green on exactly one machine. `backend/requirements.txt` exists
now, `pr.yml` has a backend job, and `ci` replays `make spans` itself rather than assuming
a `out/` directory that `.gitignore` deliberately withholds.

**Do not pass `PY=python3.12`** unless `python3` is not 3.12+. This file used to; the flag
fails outright under pyenv when 3.12 is installed but not shimmed, and an empty `PY=`
resolves to the memorable `make: m: No such file or directory`. The default is `python3`.
Verified on 3.14.7.

## First-time setup — the `.env` nothing told you to make

```
cp .env.example .env
```

**Do this before any of the six procedures.** `.env` is gitignored (it holds a real
`OPENAI_API_KEY`), it is read by `serve-api`, `smoke`, `spans`, `report`, `calibrate` and
the spike targets — and until the cold run, no document in the repo ever told an operator
to create it. Three of the six procedures fail without it, the first with
`RuntimeError: MODEL_ANALYZE is unset`.

**`.env.example` is not usable as copied.** Two values have to be set by hand:

| Key | Set it to | Why it is not already there |
| --- | --- | --- |
| `MODEL_ANALYZE` | `gpt-5-mini-2025-08-07` for offline work | Ships empty. The value that makes the fully-offline path run was written down **only in `.github/workflows/pr.yml`** — replay verifies the (model, prompt) pair a cassette recorded, so `MOCK_LLM=1` still needs the id |
| `DEMO_MODE` | `cached` | Ships as `live`, which contradicts every other statement about how this demo is run |

With those two, the whole offline path works with no key, no GPU and no network.

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

**Bring the demo up with P1, not with `make demo`.** `make demo` is `docker compose up`,
which predates ADR-003 and is a second, container-shaped answer to a question P1 already
answers natively. Two documented ways to start the same demo is one too many for a document
somebody reads at 9pm, and the cold run hit the disagreement immediately. P1 is the
procedure; `make demo` is kept for the compose path and is not the one to reach for.

The spend guard survives at a token $5/$10, purely against a runaway loop.

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

## The eight operating procedures (M3-5a, plus P7 from M3-6 and P8 from M3-1b)

**Every procedure below was executed once before it was written down.** That is M3-5a's DoD
and it is not ceremony: a runbook written from the source is a description of what the
author believes the commands do, and the gap between that and what they *do* is exactly the
gap an operator discovers at the worst moment. Each entry names what it produced when it
was run, so a reader can tell whether their run matched.

### P1 — Bring the demo up

```
make report              # span trees -> out/reports. 14 reports, offline, ~20 s
make fe-build-measured   # static export -> frontend/out
make serve-api           # localhost:8000, cache-first, DEMO_MODE from .env
```

**Three corrections from the cold run, and the middle one shipped the wrong demo.**

- **`make fe-build-measured`, not `make fe-build`.** `fe-build` builds against the
  *committed fixtures* — `fx-` items, invented to exercise states the measured corpus does
  not contain. `fe-build-measured` builds what the demo ships. Following the old line
  literally brought up a site serving **invented data**, and `make smoke` caught it as
  `an item page resolves through the mount — 404`, which is the smoke test doing its job
  against a runbook that was wrong.
- **`make report` comes first.** `out/` is gitignored because it is derived, so a fresh
  checkout has an empty cache and P2 fails four checks before it can prove anything.
- **`make fe-build*` no longer needs `make fe-install` first.** It did, and P1 never said
  so, so the first command of the first procedure died on `sh: next: command not found`.
  The build targets now install the toolchain if it is missing.

`/readyz` is the check that matters, not `/healthz`. It reports `cached_reports`,
`stale_reports` and the breaker state. **A green `/healthz` with an empty cache is a demo
with nothing to show**, which is why readiness reports what it is ready *for*.

### P2 — Prove the demo works before an audience sees it

```
make smoke
```

Starts a real server **with `OPENAI_API_KEY` stripped**, runs **22** checks, stops it. *We
did not call the provider* and *we could not call the provider* are different claims, and
only the second proves the fallback product.

**It needs P1 to have run first** — all of P1, including `make report`. The check count is
22 and this file said 16 for a week; the number moves when checks are added, so trust the
output over this line.

> **Observed on first run (12 Sep):** 4 of 16 failed, and every failure was real — two
> stale reports, a thin cache, and a breaker pointed at a directory.
>
> **Observed on the cold run (18 Sep):** 4 of 15 failed on an empty checkout, then 1 of 22
> after `make report`, and that last one was **the runbook's own error** — P1 said
> `fe-build` where the demo needs `fe-build-measured`, so the site served fixture items and
> no measured item page resolved. **22/22 after the fix.**
>
> Do not treat a red smoke run as flaky. It has never produced a false alarm, and on the
> two occasions it went red it was right both times — once about the system, once about
> this document.

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
make report            # span trees -> out/reports, one report per item (--all is the default)
```

> **This command did not run as written.** A bare `make report` exited 2 with `rlens: error:
> one of --item or --all is required`, and the repair hint `make smoke` prints on an empty
> cache said the same wrong thing. The author always typed `ARGS="--all"`; the document
> never learned it. `--all` is the default now — `make report ARGS="--item mb-01"` still
> does the single item. This is the sharpest thing the cold run found, because P4 is the
> procedure every staleness guarantee and E4 itself rest on.

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

`make faithfulness-check` and the calibration-page grep both run in CI — **genuinely, as of
the cold run.** Both were in `make ci` and in no workflow, and `faithfulness-check` could
not have run anywhere but the author's laptop regardless: it reads `docs/spikes/S4-raw/`,
which `.gitignore` excluded. Those records are the denominator of B4 #6's published *0 of
48*, so they are committed now (40 KB) and the check is runnable by anyone verifying it.

> **`make calibrate` used to erase B4 #1, and it did it quietly.** A bare dev run wrote
> `inter_annotator.behavior = null` over the measured κ 0.867 / 0.935, under a note reading
> *"the second annotator has not labelled yet"* — false since 15 Sep. FE-6 renders this
> file verbatim, so the calibration page would have gone back to *not yet measured*, which
> reads as an honest empty state rather than as an erasure.
>
> **Fixed:** a dev pass does not read the double-labelled steps, so it now carries the
> measured block forward and flags it `carried_forward` rather than nulling it. `--iaa` and
> `--final` do read them, so a null from either is still written — it is a measurement.
> Both halves are tested, and the first is negative-tested.

### P6 — Hand the analyzer to someone else

```
make wheel
```

Builds the wheel, installs it into a venv with nothing else in it **outside the repo**, and
ingests a third-party LangGraph capture. This is the real handover artifact.

> **Observed on first run:** it failed. The JSON Schema was not packaged, so `load_schema()`
> raised in any fresh install while the whole test suite stayed green from the source
> checkout. **Run this after touching `analyzer/`, not before a release.**

### P7 — Re-record the fallback demo video (E15)

```
make fe-build-measured        # the video must show the demo that ships, not the fixtures
make demo-video
```

Records **one continuous unedited pass** over five surfaces at 1280×800 (~49 s) into
`docs/demo-fallback.webm`, with provenance in `docs/demo-fallback.json`. It starts its own
server, strips `OPENAI_API_KEY`, and stops the server afterwards — you do not need `make
serve-api` running first, and if you do have one running, pass `ARGS='--base-url
http://127.0.0.1:8000'` instead of starting a second.

**`playwright` is a demo-only dependency and is deliberately not installed by `make
install`.** If it is missing this fails with the install line rather than being skipped:

```
.venv/bin/pip install -r scripts/requirements-video.txt
playwright install chromium        # only if no build is already cached
```

> **It refuses rather than recording something wrong.** No mounted export → exit 1 naming
> `make fe-build-measured`. Any stale report → exit 1, because a recording of numbers
> attributed to a system that is no longer running cannot be re-checked by whoever watches
> it. Any page not returning 200 → exit 1 after writing the file, so you can see what it
> caught.
>
> **Observed on first run (23 Sep):** the server never came up, and the recorder said only
> *"never became ready"* until it was changed to keep the server's output. The real error
> was `ValueError: could not convert string to float: '10  # was 150...'` — the recorder had
> re-implemented `.env` parsing in Python and did not strip the trailing inline comments
> this file's own `.env` carries. **It now sources `.env` through the shell, exactly as
> `make serve-api` and `make smoke` do**, because a second interpreter of that file is a
> second thing that can disagree with it.

**Re-record it when the shipping export changes**, not on a schedule. A video of last
week's page is the same class of problem as a stale report, minus the guard — the sidecar
records the commit so the two can at least be compared.

### P8 — Run a live re-run, and watch it (E2)

```
DEMO_MODE=live MOCK_LLM=0 make serve-api
# then, against a real bank id:
curl -s -X POST localhost:8000/api/runs -H 'content-type: application/json' -d '{"item_id":"mb-06"}'
curl -N localhost:8000/api/runs/<run_id>/events      # the progress stream
curl -s localhost:8000/api/runs/<run_id>/report      # what it built, flagged live:true
```

Or open any item page while the server runs with `DEMO_MODE=live`: the **Re-run this item
live** panel appears at the bottom and streams the same events. It renders **nothing** when
live runs are off, which is deliberate — a control that offers to re-run a model and then
fails is worse than no control, because the reader cannot tell whether the demo is broken or
the feature is switched off.

> **`MOCK_LLM=1` is the default in `.env`, and a run under it is NOT a live run.** It replays
> cassettes and finishes in well under a second. That is a perfectly good test of the
> plumbing and it is not evidence the model was called — *"we did not call it"* and *"we
> could not call it"* are different claims, and so are *"we called it"* and *"we replayed
> it"*. **If a run finishes in under a second, it did not talk to a model.**
>
> **Observed:** mb-01 in **97 s**, mb-06 in **42 s**, with `gpt-oss:20b` warm in ollama.
> Most of that is local generation.

**This spends real analysis calls.** Three per run, one per arm. The dollar breaker cannot
see them — `analyzer/prices.json` is deliberately unpriced, so nothing can convert tokens to
dollars honestly — so the guard that actually binds is the **call budget** in
`backend/runs.py` (`LIVE_RUN_CALL_BUDGET`, `LIVE_PROCESS_CALL_BUDGET`), reported by
`/readyz` as `live_run_budget`. Read `spent_usd: 0.0` as *"nothing here can price this"*,
never as *"this was free"*.

**The report a live run builds is not a published measurement.** It carries `live: true`, no
`measurement_context`, and it was never stamped. It is one unrepeated run. The cached report
at `/api/report/{id}` is the number everyone else sees, and the two genuinely differ — a
live `mb-06` returned `direct` with 2 steps where the cached report has 3, one `unsound`.

---

## Deploy

**There is none.** The demo runs from a laptop ([ADR-003](decisions/ADR-003-hosting.md)): no
domain, no registry, no cloud service, no rollback, no rate limiting, no iframe embed.

What survives: `make smoke` against `localhost` as the acceptance script, a clean-venv
install proof plus the analyzer wheel as the real handover artifact, and a fallback video —
because one laptop is a single point of failure and pretending otherwise is how demos die.
