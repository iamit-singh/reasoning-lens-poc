# Hours ledger

One line per work session (C10.5). Reviewed at month end; **the cumulative figure is what
releases the Option-2 contingency at G2.** This file is the C10.1 contingency trigger —
keep it honest, including when it is unflattering.

> **The live tracker is the shared view of this same data:**
> [Reasoning Lens Month 1](https://claude.ai/code/artifact/d80de125-0d48-4546-a7b4-d1642af07ede)
> — task status, hours, the G0/G1 checklists and the Appendix D decisions. It is backed by
> a database, so it is what other people read. **Update both, or update the tracker and
> regenerate this file** — two ledgers that disagree are worse than one.

| Date | Week | Task | Hrs | Note |
|------------|------|-------|-----|--------------------------------------------------|
| 2026-09-10 | W1 | D0 | 0.3 | Day-1 unblock: four Appendix D asks drafted. **None sent** — each needs a human. D#1 default taken and recorded (Option 2, L1+L2 applied now) |
| 2026-09-10 | W1 | M1-3 | 0.4 | S5 DNS: ADR-003 written, ticket text ready to file verbatim. **Not filed** — no ticket ID, no named owner yet |
| 2026-09-10 | W1 | M1-1 | 0.8 | S1 harness written + self-tested (alias refusal, no-key path). ADR-001 committed as *Proposed* with all 4 branches pre-decided. **Run blocked: no API key** |
| 2026-09-10 | W1 | M1-0 | 1.5 | CI green across all 9 every-PR jobs; import-linter contract proven by a deliberate violation (`23defe3`) then reverted (`7b1ae59`) |
| 2026-09-10 | W1 | M1-1 | 1.2 | **Plan amendment 001**: hybrid runtime (local generation + OpenAI analysis), local-only demo, solo delivery. ADR-001 + ADR-003 rewritten; pin redefined as a tuple; S1 re-scoped; S6 tool-calling spike added; config, Makefile and 22 unit tests updated |
| 2026-09-10 | W1 | M1-15 | 0.8 | **W2-0 pulled forward** — M1-1/G0 was blocked on it. ollama 0.33.3 served natively; `gpt-oss:20b` pulled; full pin tuple recorded in `.env` **and** ADR-001. **0.3 over estimate**: two defects in `pin_local.sh` — it recorded ollama's truncated manifest id as the digest, and emitted `LOCAL_RUNTIME` unquoted so sourcing `.env` silently truncated it |
| 2026-09-10 | W1 | M1-1 | 0.6 | **S1 local arm: PASS.** 2535 chars of raw reasoning in a `reasoning` field, not inline `<think>` tags. ADR-001's G0 table filled from the real run. **G0 check 2 closed off as NOT met** |
| 2026-09-10 | W1 | M1-16 | 0.6 | **S6: PASS, 20/20** — 100% on all four scenarios incl. tool-choice and the false-positive check. Arm 3 is buildable; the `qwen3:14b` fallback is not needed |
| 2026-09-10 | W1 | M1-1 | 0.5 | **G0 check 2 closed.** `tiktoken>=0.9` declared; `o200k_harmony` counting wired into `make spike-s1`. **741 reasoning tokens, 73.4% of output**, reconciling to the runtime's billed 1020 within a +10 structural residual. `LOCAL_TOKENIZER` joined the pin tuple |
| 2026-09-10 | W2 | M1-2 | 2.1 | **S2: complete.** Stock LangGraph agent, 15 spans, fixture committed. 6 C3.1 rows confirmed, 2 corrected, **1 absent**. **No `gen_ai.*` attribute arrives at all** — the live namespace is OpenInference `llm.*`, so five of nine rows were dead. **Reasoning text never reaches a span**; the control proves the runtime sends it and LangChain drops it. ADR-002 filed. **0.6 over the 1.5 h estimate** — see the W2 note
| 2026-09-10 | W2 | M1-6 | 3.4 | **Runner arms 1–2 done.** `llm.py` provider abstraction, ADR-002 emission, 22 contract tests green under MOCK_LLM. **ADR-004: arm 1 cannot have thinking *off*** — `reasoning_effort: none` and native `think: false` are both **silently ignored** (2918 chars returned); `low` is honoured (131). Arm 1 becomes a *minimal*-reasoning baseline and B4 #7's claim narrows. Regime separation is verified from output, not the request. **+0.4 over the revised 3.0**
| 2026-09-11 | W2 | M1-4 | 2.0 | **Bank done, W2 closed.** 14 items under L1; floors met at 5 `tool_required` / **4** traps / **4** `easy` / 6 `multi_step`. Checkers in `rlens.checkers` so the bank is validated by the code that will grade the runs. **ADR-004's control group verified on real runs: mb-01 correct on BOTH arms at 5 vs 21 reasoning tokens.** +0.3 over estimate
| 2026-09-11 | W3 | M1-5 | 2.6 | **Trap reproduction measured. DoD NOT met: 0 of 16 candidates earned the tag over 120 runs**, 117 correct, 1 trap hit. Threshold held, not lowered: 12 further candidates authored in two rounds (round 2 abandoning word-problem arithmetic for inclusion–exclusion, combinatorics, compounding). **ADR-005 filed as *Proposed*** — there is no shallow regime on this model to trap, so the arm contrast is difficulty, not misdirection. **+1.1 over the 1.5 estimate**: the DoD asks for "3 of 5 runs" and the committed pin is greedy-decoded, so the two-regime design (pinned + sampled) had to be worked out and justified before a single run was worth making |
| 2026-09-11 | W3 | M1-5 | 1.2 | **Two grading defects, neither about traps, both found only because M1-5 is the first task that grades real model output.** (1) `exact` was a string compare, so `7 minutes` scored **wrong** against a declared `7` — **18 of the first 48 runs, 37.5%**. It is now numeric-aware, refusing negation and multi-number ambiguity; `test_checkers.py` (27 tests) grades the shapes a model actually writes. (2) The answer extractor returned `\]` from a LaTeX display block, and the line above it carries four numbers — so `unparsed` is now a first-class outcome, separate from wrong. **Fully unbudgeted.** Would have surfaced in M3 as "the model is worse than expected" |
| 2026-09-11 | W3 | M1-5 | 1.2 | ADR-005 (four options, recommendation, consequences) · `test_trap_reproduction.py` — M1-5's DoD as a **strict `xfail`** so the shortfall cannot be lost and cannot drift in either direction, plus 8 contract tests over the committed evidence · bank README rewritten so `is_trap` reads as a declaration · `make lint` widened to the repo, which `ruff.toml` already claimed to cover while only `analyzer/` was checked |
| 2026-09-11 | W3 | M1-5 | 1.4 | **ADR-005 accepted (option B) — and implementing it found its second half false.** B said "re-point FE-1 at the verified difficulty contrast"; that rested on an **ad-hoc probe**, so the contrast was measured across the corpus first. **0 of 16 items separate the arms** (14 bank + 5 harder candidates; 11 agreed, 3 are `tool_required` run without tools). Cause: **arm 1's `low` effort is ADAPTIVE** — 3 reasoning tokens on `mb-03`, **407 on `hm-02` against arm 2's 423**. Harder items close the cost gap without opening an accuracy gap, so there is no difficulty band where arm 1 fails and arm 2 does not. **ADR-006 filed as *Proposed***. Trap floor withdrawn and the four declarations retired into `traps/candidates/` with `retired_from`, so the log still renders them. What FE-1 can feature: the **cost** contrast (1.2–13.3× for the same answer, 11 of 11) plus the **tool** contrast, unverified until M1-7 |
| 2026-09-11 | W3 | M1-7 | 3.4 | **Arm 3 done. DoD MET: 3 arms runnable from the CLI on every bank item; `react` 14/14 vs 11/14 for arms 1-2.** ReAct loop on the provider layer, `max_turns=6`, AST calculator (no `eval` -- the expression is model output), 12-fact L2 corpus, TOOL spans in the stock-LangGraph attribute names. **ADR-007: not LangGraph, and the probe is the reason** -- on a tool-calling turn `content` is EMPTY and the whole thought is in `reasoning`, the field S2 proved LangChain drops, so a LangGraph arm 3 would emit a perfect ReAct trace with every `thought` step blank. All three DoD checks verified explicitly: `max_turns` trips cleanly, `mb-01` terminates in 1 turn 0 calls, a lookup miss returns a well-formed negative observation that names the keys and the model recovers on the next turn. +0.4 over the 3.0 |
| 2026-09-11 | W3 | M1-7 | 0.6 | **ADR-006's open row closed on corpus evidence: arm 3 turns 3 wrongs into rights** (`mb-08`/`mb-09`/`mb-10`) **and is 24-50x cheaper doing it.** On `mb-08` arm 2 spent **3,966 reasoning tokens failing to recall a fact that does not exist** -- every place name is invented, on purpose -- while arm 3 spent 80 and looked it up. That pair is the product in one frame and is a better demo row than the difficulty contrast the plan expected. Also: **2 of 5 `tool_required` items had arm 3 call NO tool** (`mb-06`, `mb-07`), so the tag is a claim like `is_trap` was; the measured share is in `arm-contrast.md`. Contrast harness extended to 3 arms; 42 runs |
| 2026-09-11 | W3 | M1-7 | 0.5 | **A cwd-relative data path that would have failed silently.** `problem-bank/corpus/facts.json` resolved relative to the working directory, so it only worked from the repo root -- and a missing corpus raises inside a tool call, which the loop is DESIGNED to swallow into an observation. From anywhere else arm 3 would have run, called `lookup`, received `no fact corpus at ...` as a well-formed observation, and answered wrong on a green run with a plausible chain explaining why. `runner/paths.py` resolves env -> cwd -> checkout and names every place it looked; `load_item` had the same latent bug and is fixed with it. Found by the first test that ran from `analyzer/` |
| 2026-09-11 | W3 | M1-7 | 0.8 | 52 tests across `test_tools.py` (35 -- the calculator whitelist tested as the security boundary it is: `__import__`, `open`, lambdas, huge exponents), `test_react_loop.py` (17 -- the loop driven by a SCRIPTED provider, because a cassette cannot be made to produce a six-turn runaway or a tool-name typo on demand) and 6 arm-3 contract tests replaying real cassettes with the tools NOT mocked. **One test earned its keep immediately**: it caught arm 3 emitting `input.mime_type`, which the stock LangGraph capture does not -- dropped, since "plausibly in the spec" is not the standard, "observed in a real trace" is. 49 cassettes recorded (224 KB), so MOCK_LLM CI now covers the whole bank x arms matrix |
| 2026-09-11 | W3 | M1-8 | 2.4 | **Segmenter done. DoD MET, and `segmenter-frozen-v1` TAGGED.** C4.2 in full: ReAct structural path, discourse + list markers, the merge, the split cap, `step_id` and `char_range`. 12 goldens covering every row of §5.3's table, each 3x byte-identical. Everything works on `(start, end)` index pairs into one normalised string, so offsets are exact by construction and `char_range` indexes something the trace actually carries. **M1-6 left `contracts.py` and `ingest/otel.py` as skeletons and M1-8 inherited both** — a segmenter cannot be byte-stable over an input that does not exist. +0.4 over the 2.0 on the segmenter itself |
| 2026-09-11 | W3 | M1-8 | 0.9 | **ADR-008: the token unit is a WORD, and C4.2 does not name a tokenizer.** `tiktoken.get_encoding` **fetches a remote BPE file** — a segmenter whose 15/200 thresholds depend on whether that download succeeded is not byte-stable, and the failure is SILENT: it does not error, it segments differently, and every `step_id` shifts. A scheduled instance of Hazard 1, fired by a cleared `/tmp`. Thresholds converted rather than reinterpreted, at a ratio measured over this project's own traces (**7,531 words / 10,890 harmony tokens = 1.446**): merge 10 words, split 138. `138` kept rather than rounded because it is derived. A test parses `segment.py`'s imports and fails on anything outside `{__future__, itertools, re, rlens}` |
| 2026-09-11 | W3 | M1-8 | 1.3 | **Two defects found by segmenting the corpus, not by reading the code.** (1) A trace with reasoning but **no visible answer** reported `trace_quality: "full"`. `mb-08.thinking` produced 141 reasoning steps and EMPTY content — the model looped 126 times on a fact that does not exist and never answered. Downstream that becomes `correct: false`, asserting the model answered and was wrong when it never answered: **M1-5's `unparsed`-vs-`wrong` distinction one layer up**. Now `partial`, in the runner AND in ingest's fallback, by the same rule. (2) An **unterminated code fence** was unprotected, so a 70-word trace truncated mid-fence split into four steps, three of them lines of code. C4.2 says never split inside a fenced block, not "inside a fence that closes" — and S3 measured `finish_reason: length`, so truncation is observed. Unterminated maths deliberately NOT protected: over-protection has a cost too |
| 2026-09-11 | W3 | M1-12 | 1.9 | **S3 done, and it ran BEFORE the tag as §5.3 requires.** Its verdict lands on M1-9, not the segmenter. **The split cap fires on 0 of 261 thought steps** (longest 130 words, median 21); five traces exceed it and the marker splits had already broken each below it, so no segmentation that exists today depends on the cap and a later change cannot renumber anything — **that is the condition the freeze needed.** And **"25 is too many" is FALSE**: the compat endpoint's `max_tokens` is **silently ignored** (16000 still returned `finish_reason: length` at ~1,854 tokens, three runs byte-identical), and against the native endpoint with `options.num_predict` batches of 10, **25 AND 50** all return a row per step with exact `step_id` match. **Fifth parameter accepted and ignored.** Analysis calls also need `think: low` — at the default effort a 25-step batch spent its whole budget in the reasoning channel and returned empty content while billing 2,293 tokens. +0.9 over the 1.0 |
| 2026-09-11 | W3 | M1-8 | 0.4 | Answer extraction moved to `rlens.checkers` so the runner, the segmenter and both measurement harnesses share ONE implementation — `rlens.runner` sits ABOVE `rlens.segment` in the layer contract, so the segmenter could not have reached it where it was, and duplicating it is the mistake M1-5 already paid for. `make spans` replays all 42 trees from cassettes (no GPU, no network); `out/` gitignored. The `rlens` CLI was still claiming it was waiting on M1-6, which shipped two tasks ago |
| 2026-09-11 | W4 | M1-1 | 0.7 | **G0 check 5 closed — the last open check, open since W1, and it was never technical: there was no key.** `MODEL_ANALYZE=gpt-5-mini-2025-08-07`, `MODEL_ESCALATE=gpt-5-2025-08-07`, both exact dated ids, both **probed live before being written down** — appearing in `/v1/models` is not the same as answering. JSON mode, `reasoning_effort: low` and `max_completion_tokens` all honoured, verified from the OUTPUT. gpt-5 is **5x the wall clock of gpt-5-mini** on an identical request (19.9s vs 3.8s): that is the argument for tiering as a number, and why `ESCALATION_MAX_STEPS` is a cap. **And S1's deferred half is now a measurement**: against the pinned tier, **384 reasoning tokens billed, 0 chars of reasoning text returned.** ADR-001's load-bearing premise had been asserted, not shown — uncomfortable in a project whose whole thesis is the difference. Arm 2 cannot be built on OpenAI; the local runtime returns 2,535 chars for the same probe. **G0 is 6/6.** `25adc21` |
| 2026-09-11 | W4 | M1-9 | 3.6 | **Classifier v0 done, and S3's three findings are structural rather than remembered.** Chunk with a cap and stitch on `step_id` (25 is a cap, not a batch size — traces run 2 to 141); `reasoning_effort: low`; the output cap asserted from the OUTPUT, with `finish_reason: length` raising rather than retrying, because a truncation reproduces exactly and calling it a parse failure names the wrong cause. **Later chunks carry their preceding steps** — "sound GIVEN ONLY the preceding steps" is unanswerable without them and a model asked anyway would answer plausibly on no evidence. Nothing fabricates a label: missing/extra/duplicate ids fail, the repair retry runs once and is handed the validation error, a second failure degrades the whole strategy and renders unannotated. `analyze()` went into `llm.py`, **reversing a note M1-6 left there** — the C2.2 grep's strength comes from classify/judge/consistency being clean, so a third provider-aware module would weaken the claim, not strengthen it. `cd166e0` |
| 2026-09-11 | W4 | M1-9 | 0.9 | 31 tests, almost all failure paths, driven by a **scripted stub rather than cassettes**: a cassette cannot be made to drop row 17 of 25 on demand, and row 17 going missing is the event this module exists to handle — the same argument `test_react_loop.py` made for arm 3. Also fixed `check_provider_symbols.sh`, which was failing on the English word **"coherently"** (it contains `cohere`); word-bounded now and verified to still catch real imports. A check that fires on prose is a check people learn to work around, and the next thing worked around is a real hit |
| 2026-09-11 | W4 | M1-10 | 2.4 | **`ReasoningReport` schema committed and the G1 freeze is mechanical.** `additionalProperties: false` at every level — without it the schema permits everything and G1 freezes a document that says nothing; `schema_version` is a `const` so a half-done version bump fails. Every Month-2/3 field present and **nullable**, and Month 1 writes an honest null: a `measurement_context` of zeros renders as "kappa 0.0", a measured failure, where the truth is "not measured yet". Two rules enforced rather than trusted: a `contradicts` verdict must cite a step, and `correct` is nullable because `unparsed` is a third outcome. `pipeline.py` assembles it; `python -m rlens` does what it has claimed since W1. `c62ae2f` |
| 2026-09-11 | W4 | M1-10 | 1.1 | **Four fixtures, not three, and the fourth is a finding.** §6.3 wanted `report_nominal` harvested from a real run covering all 5 behavior classes. Over a full bank x 3 arms pass the classifier produced **linear 252, verification 35, subgoal_setting 22, backward_chaining 1, backtracking 0** — no trace on this corpus contains five classes, so no harvested report can satisfy G1 check 3. Rather than hand-author a file called "nominal" and let the frontend owner assume it came from a run, both exist and each says which it is, with tests asserting authored fixtures carry `fx-` ids and a `fixture000000000` pin and the measured one carries neither. 36 contract tests execute G1 §8.2 rows 1-6 as code |
| 2026-09-11 | W4 | M1-10 | 0.8 | **`step_id` was not unique across the corpus** — `direct:direct-llm-0:0` was the first step of all 14 items, and 310 steps collapsed to **155 distinct ids**. C3.2 calls it "the join key for every label ever written" and it was not a key. `NormalizedTrace` enforces uniqueness *within* a trace, which is exactly what hid it: every trace was individually valid. **Found by M1-11's sampling draw on its first run**, which reported 19 steps drawn from a four-step trace — and found *before a single label existed*, which is the entire reason the plan puts the draw ahead of the labelling pass. In W6 it would have surfaced as a kappa that made no sense against 40 human labels that could not be repaired. Fix keeps determinism (a random id would have bought uniqueness by giving up replay and the goldens); ordinals did not move, so no text changed step. `8970fbc` |
| 2026-09-11 | W4 | M1-11 | 1.9 | **Rubric v1, written for Ankit rather than for its author** — he reads it cold in W6, so it opens by telling him not to ask, and every hard case is decided in advance and binding even where he disagrees. Five worked examples, five adjudicated hard cases drawn from what actually happens on *this* corpus (a `wait` that reverses nothing; a restatement — and one trace repeats a sentence 126 times, so that case is not hypothetical). **The taxonomy block is byte-identical to the classifier prompt and CI enforces it**: if they drift, kappa measures the wording and reports it as classifier quality. `check_rubric_drift.sh` was verified to FAIL on a one-word change before being trusted to pass, and lives in `scripts/` because I1 makes the analyzer standalone. `58434a9` |
| 2026-09-11 | W4 | M1-11 | 0.7 | Blind labelling tool — **blind by construction, not by discipline**: it does not import `rlens.classify` at all and withholds the known answer and the rest of the trace, so C6's outcome-bias guard is a property of the tool rather than a line in a prompt. Skips are recorded as data. `sampling.json` carries seed 20260930, the method, the commit and the ordered 90 ids; `answer` steps are excluded from the population with the reason written down, and the **cost of that exclusion recorded too** — the classifier does emit rows for answer steps and those sit outside the measured population. **The 40 labels are NOT written and must not be**: they are human ground truth and generating them would corrupt the one claim this PoC exists to make |
| 2026-09-11 | W4 | M1-13 | 2.1 | **S4 done. 0 of 48 trials flipped** — metadata leak, authority, sycophancy and the few-shot pattern, every cue type Appendix A.4 names, across two problem regimes. **M2-9 plans 12 candidate pairs to find 3; on this evidence it finds 0**, and that is the answer S4 was bought to deliver in W4 rather than in W7 with 3.5 h spent. Not a plumbing failure: **the model verbalises the cue** — names the hint, discusses it, answers what it was going to answer anyway. Two corrections the first pass forced, both of which would have produced a wrong number quietly: the answer reader was letter-only and the model answers option *values* (`1887`, not `B`), silently dropping two of three unverifiable problems as "no baseline"; and the first pass used only **solvable** problems, which measures the problems as much as the cues — refusing a hint you can check is not evidence of faithfulness. Second finding, possibly the larger: **2 of 3 unverifiable problems returned EMPTY content**, zero characters with reasoning tokens billed. Asked something it cannot look up, this model does not guess, it loops — the `mb-08.thinking` shape again. **ADR-009 filed (Proposed)**: publish the negative result; M2-9 re-scoped 3.5 h → ~1.0 h, **the first task in Month 1 to give hours back**. `31c1cee` |
| 2026-09-11 | W4 | M1-10 | 0.6 | **Two defects the pipeline found by running on real data, not by review.** (1) `known_answer` can be a **list** — `set_match` items carry `['red','green','blue']` and the schema typed it string-only; caught by the full-bank replay rejecting a real report, which is the G1 freeze working in the week it was meant to. (2) **An analysis failure sank the whole report**, losing two good arms to one bad call against B6.5. It now degrades one arm — and `status` stays `ok`, because the schema is explicit that `failed` means the *generation* call did not return and this arm generated fine. Calling it failed would tell a reader the model never answered: **the `unparsed`-vs-`wrong` distinction M1-5 and M1-8 each paid for, arriving a third time in a third place.** That fix then quietly weakened the mock tests — a missing cassette also became a degraded arm, so "the report validates" passed with zero cassettes and every arm blank; replay is now asserted positively |
| 2026-09-11 | W4 | M1-14 | 0.7 | Recorder verified end to end on one item: record live → replay under `MOCK_LLM=1` with the socket broken → identical report. Analysis cassettes are recorded **by running the ordinary pipeline** with `RECORD_CASSETTES=1`, so the captured call is the production call rather than a harness re-issuing something similar. Each carries the sha of its own request and replay **refuses a mismatch** — that is what "keyed by a hash of the request" buys without making the directory unreadable, and it turns a stale cassette into a loud failure instead of a green CI run asserting behaviour that no longer exists. **Also fixed two CI jobs that would have gone green over nothing**: `run_marker.sh` called `../.venv/bin/pytest`, which does not exist in CI (exit 127 on every run since W1), and its skip check never fired because it was anchored while pytest writes `2 passed, 5 skipped, 330 deselected` |
| 2026-09-12 | W5 | M1-9 | 1.3 | **ADR-010: the taxonomy barely populates, and the confound was checked before the conclusion was drawn.** 81% of steps are `linear`; `backward_chaining` has **1** instance in the whole corpus and `backtracking` has **0**. A zero has two readings with opposite consequences — *this model does not backtrack* is a claim about the corpus, *the classifier cannot detect it* is a claim about the classifier — and **nothing in the classifier's own output separates them.** So `make taxonomy-coverage` measures the corpus with **no model at all**: how many steps open with a surface marker the frozen segmenter already treats as a discourse signal. **11 of 261 thought steps (4.2%), in 2 traces of 42** — and all eleven are *"Actually there is a Fairhaven in New Zealand? I think there is a Fairhaven in New Zealand?"*, inside the looping traces, opening with a backtracking marker and reversing nothing, which `rubric.md` hard case 4.2 adjudicates as `linear` in advance. The classifier's zero is **plausible rather than proven wrong**, and only a human reading those steps settles it — which makes M1-11's 40 labels the most valuable 1.5 h left in the month. **Third phenomenon the plan assumed that this model does not exhibit.** `e5e0ff0` |
| 2026-09-12 | W5 | M1-11 | 0.2 | `--dry-run` for the labelling tool, because smoke-testing it **wrote a fake label into the corpus**. The file was the one artifact in the project whose whole value is that every row in it was written by a human looking at a step. Caught immediately; the guard is cheaper than the habit of remembering. `411a704` |
| 2026-09-12 | W5 | M2-13 | 2.3 | **Calibration scoring CLI — κ, per-class F1, the majority-class baseline and bootstrap CIs. 1.5 h planned, +0.8.** The overrun is the reason to trust it: **κ is checked against scikit-learn to 10 decimal places over 300 randomly generated label sequences**, including the degenerate cases that break naive implementations (perfect agreement, total disagreement, one annotator constant). A κ this project computes itself is the headline number at G2; an implementation that agrees with the reference on 300 adversarial inputs is evidence, and one that was merely read over is not. `4a444aa` |
| 2026-09-12 | W5 | M2-12 | 0.8 | **`docs/findings.md` — the four negative results in one place, each re-runnable by a named `make` target.** B0 Condition #5 commits this project to publishing whatever the numbers are; this is where that is kept rather than promised. Traps that do not reproduce, arms that do not separate, cues that do not move an answer, a taxonomy that barely populates. **Not four failures — one finding arrived at four times: the instrument works, and the effects it was pointed at are smaller than the plan expected.** A second section lists the defects fixed rather than published, and three of them share one shape: *we could not read it* reported as *it was wrong*, in the answer checker, in `trace_quality`, and again in the report's arm status. Prep for M2-12, not the gate report itself. `a6845ae` |
| 2026-09-12 | W5 | M2-4 | 0.7 | **Prep: is `validity_confidence` a signal or decoration?** C4.4's escalation policy rests on one float — two of its three conditions are thresholds on the same number — so a classifier emitting a narrow band degenerates the policy to "re-judge the flagged ones" and the frontier tier never sees a low-confidence-but-sound step. **That failure is invisible from outside**: escalation still runs, the report still carries `escalated`, the rate still looks plausible. On a 17-row sample it already reads badly — confidences banded 0.75–0.95 so the 0.70 threshold selects **nothing**, and **64.7% of rows carry byte-identical behavior and validity confidences**, the model emitting one number twice rather than judging two questions. Too small to conclude from; the full-corpus histogram lands after the M1-9 measurement, which uses the same tier. `a8745f5` |
| 2026-09-12 | W5 | FE-1 | 3.2 | **Shell, featured comparison, item picker, routing, mobile — pre-rendered, no backend. 1.5 h planned, +1.7.** The overrun is almost entirely the first surface paying for the toolchain the other seven inherit. **The featured comparison had to be re-pointed twice before it was true**: ADR-005 killed the trap contrast, ADR-006 killed the difficulty contrast, and what it now features is the tool contrast (`mb-08`/`mb-09`/`mb-10`) plus the cost contrast — the two things measurement actually supports. `ee21b69` |
| 2026-09-12 | W5 | FE-2a | 1.4 | Annotated trace renderer, first half — **2.0 h planned, −0.6.** The five behavior definitions in the legend are **parsed out of `calibration/rubric.md` at build time** rather than retyped into a component. The rubric, the classifier prompt and now the UI legend are three places the same five sentences could drift apart, and κ measures rubric drift the moment they do. `70db531` |
| 2026-09-12 | W5 | FE-3 | 1.0 | **Scoreboard + verdict line — 2.0 h planned, −1.0.** Built with FE-4 in one sitting off the same frozen report; the pair came in **3.5 planned against 1.8 actual**, because both render from the frozen report and the fixtures were already there. **The components found a fixture gap**: nothing in the set exercised a report with a flagged step *and* a populated `measurement_context`, so the panel rendered error bars from `undefined` and showed a confident number with no caveat — exactly the I3 failure the fixtures exist to prevent. `f500377` |
| 2026-09-12 | W5 | FE-4 | 0.8 | Flagged-step side panel — **1.5 h planned, −0.7.** Renders the escalated / not-escalated badge and all five `error_type` values from `report_flagged.json`. Cheap for the same reason FE-3 was: the object it renders was frozen at G1 and the fixture that exercises it was committed before the component existed. `f500377` |
| 2026-09-12 | W5 | FE-6 | 1.2 | Calibration / limitations page — **1.0 h planned, +0.2.** B0 Condition #5's actual surface. **A grep keeps it honest**: a CI check fails the build if the page renders a metric that is not present in `calibration/results/latest.json`, so a number cannot be hard-coded into the page and survive the file it claims to come from being empty. Every metric currently renders as *not yet measured*, which is correct and is the point. `e1419ac` |
| 2026-09-12 | W5 | FE-7 | 0.4 | Report download + CTA — **0.5 h planned.** The download hands over the exact `ReasoningReport` the page rendered, not a re-serialisation, so what a reviewer opens offline is byte-identical to what they were shown. **The CTA is a mailto link, not an input box** — L6 applied, and an input box would have been the only free-text field in the entire surface. `5b57c5e` |
| 2026-09-12 | W5 | M2-8 | 1.6 | **Consistency checker (part) — 3.0 h planned for the whole task.** C4.5's question and only that question: *given only these numbered steps, does the final answer follow?* Two rules about not crying wolf, both enforced in code: a `contradicts` verdict **must** cite at least one `step_id` or it is rejected, and a trace whose steps were never annotated cannot be flagged at all. Threshold tuning and the false-positive rate are the remaining half and need labels that do not exist yet. Off behind a flag until its numbers do. `bdb887f` |
| 2026-09-12 | W5 | M2-5 | 2.1 | **Escalation tier (part) — 2.0 h planned for the whole task.** C4.4's deterministic policy, the `ESCALATION_MAX_STEPS` cap, `escalation_capped`, and the frontier verdict **replacing** the triage verdict with `escalated: true`. **The layer contract caught a shortcut**: the first cut reached from the escalation path back into the classifier's row builder, which import-linter rejected — and it was right to, because it would have made the two tiers share a code path that C4.4 requires to be independent. Off behind a flag until M2-6/M2-7 measure whether it raises recall. `fc43e30` |
| 2026-09-12 | W5 | M1-9 | 0.6 | **The 20-run measurement lost 13 runs of good data, and the harness earned two fixes.** The machine slept mid-run (run 14 records **52,289 seconds**), the network came back down, run 15 returned **0 calls and 42 hard errors** — and the harness kept going, burning runs and filling the record with noise shaped like data. The record was a single write **after** the loop, so killing it at run 15 lost 630 clean calls; it now writes after every run. And a run where *every* trace hard-errors now stops the harness and says so: a parse-failure rate computed over calls that never reached a model is not a low rate, it is no rate at all. The tier itself was fine — a probe returned in 3.0 s. `2919386` |
| 2026-09-12 | W5 | M3-1a | 0.9 | **Backend (C4.9), pulled forward — the READ-ONLY product, which is M3-1a and is the G3 fallback.** The security posture is one sentence and it shapes the whole route table: **the only visitor-controlled input in the entire surface is an item id checked against a static allowlist**, and that allowlist is the committed bank rather than a second list that could drift from it. The id indexes a dict, never a path join, so traversal cannot reach the filesystem even in principle. `GET /api/report` **never** triggers a model call — B4 #8 promises the cached path at p90 under 5 s, and a read that could silently become a two-minute generation is a read with a hope rather than a budget. `2919386` |
| 2026-09-12 | W5 | M3-3 | 0.5 | The **guards** on that route table, which are M3-3's and not M3-1a's: a rate limiter, a breaker check on the live path, and `DEMO_MODE=cached` as a kill switch that disables `POST /api/runs` outright. **None of them is verified yet** — M3-3's DoD is a *forced trip* and a Redis-partition test in `smoke.py`, and a breaker that has never been tripped is a breaker with a hope rather than a test, which is the same sentence this project has now written about a cache, a cap and a parameter. `2919386` |
| 2026-09-12 | W5 | M3-7 | 0.6 | **ADR-011 — no Redis, and the question was never *which* Redis.** ADR-003 had already deleted the deployment and left one line open: *local Redis via compose, or the filesystem cache tier*. One process, one operator: a shared cache, a shared rate counter and a shared spend total are all **coordination between replicas that do not exist**. Redis cannot make this demo more reliable and can absolutely make it less, by being down — and C10.4 already carries a fallback-video line item because a local demo has *more* single points of failure, not fewer. Compose loses a service and a healthcheck. **1.0 h planned, −0.4**, because ADR-003 had done the expensive half of the thinking in W1. `cffd8b7` |
| 2026-09-12 | W5 | M3-2a | 0.9 | Cache tier (the filesystem) + the **staleness assertion**, which is the half that matters. C2.3 makes four things part of the cache key, and a report built before any of them moved is not merely old — it is **a set of numbers attributed to a system that is no longer running**. `assert_fresh` refuses to start rather than serving them, and refuses rather than regenerating, because regenerating on a miss would make a `GET` trigger a model call. The escape hatch names what taking it means instead of being a quiet flag. `cffd8b7` |
| 2026-09-12 | W5 | M3-3 | 1.3 | **The spend breaker, and the third branch is why it has its own file.** Not two outcomes but four: under limit, over limit, *missing* file (allow — a fresh checkout has spent nothing, and a breaker that starts tripped teaches operators to bypass it), and *unreadable* file (**DENY**). *We could not read it* must never resolve to *so assume zero* — **the fourth time this project has written that sentence**, after `trace_quality`, `unparsed` and `degraded`, and the first where the lie costs money. `{"usd": true}` is in the test set because `True` is an `int` in Python and a naive check reads it as $1.00. DoD is a **forced trip**, so `trip()` is a real function on the real path rather than a simulation. **Not complete**: the Redis-partition half of the DoD is replaced by the unreadable-file test per ADR-011. `cffd8b7` |
| 2026-09-12 | W5 | M3-1a | 0.5 | **`backend/app.py` has claimed since it was written that `test_api.py` asserts its security posture "rather than trusting this paragraph". That file did not exist.** A docstring citing a test is a citation, and an uncited citation is worse than no claim, because it stops a reader checking. 27 tests now: mutating routes enumerated **from the app object** rather than a hand-kept list, traversal and injection ids, and `GET` run with both provider entry points replaced by something that raises. `make smoke` starts a real server with `OPENAI_API_KEY` **stripped** — *we did not call it* and *we could not call it* are different claims, and only the second proves the G3 fallback product. `cffd8b7` |
| 2026-09-12 | W5 | M3-3 | 0.4 | **The smoke test found a real bug on its first run, and it is the argument for fail-closed in one line.** `SPEND_FILE=` blank in `.env` made `pathlib.Path("")` the **cwd**, so the breaker was pointed at a directory. It denied every live run with `IsADirectoryError` instead of reading a zero total and allowing them — **a fail-open breaker would have passed the smoke test.** Also corrected my own smoke check: 503 is this surface's consistent convention for *not produced yet*, so the route was right and the assertion was wrong. `cffd8b7` |
| 2026-09-12 | W5 | M3-8 | 0.8 | **The wheel did not ship the JSON Schema, and only a clean venv could tell.** `make wheel` builds the wheel, installs it into a venv with nothing else in it in a temp dir **outside the repo**, and ingests the **third-party** LangGraph capture — proving it on spans we emitted would prove something weaker. It failed immediately: `package-data` listed `prompts/*.md` and not `schemas/*.json`, so `load_schema()` — which validates every report the pipeline builds — raised `FileNotFoundError` in any fresh install. **Nothing caught it and nothing could have**: from a source checkout the file is right there, so the whole suite stayed green while the handover artifact was broken. Also asserts `openai` is *absent*. **0.5 planned, +0.3.** `52dcd29` |
| 2026-09-12 | W5 | M2-9 | 0.9 | **The faithfulness panel ships, and what it publishes is the zero.** ADR-009 re-scoped this 3.5 h → ~1.0 h and it came in at 0.9. `0 of 48 trials flipped` across all four Appendix A.4 cue types and both problem regimes, so there is no set of 3 to find and nothing to over-provision against. **"0 of 48, and here is every trial" is a stronger artifact than "2 of 3 flipped"** — the second is an anecdote about a model that happened to be suggestible; the first is a measurement with a denominator, falsifiable by anyone who re-runs it against a different pin. The builder **copies** `flipped`/`verbalised` rather than re-deriving them (the adjudication is an input, not a step) and de-duplicates overlapping record files, because a trial counted twice inflates the one number the panel exists to state honestly. `faithfulness-check` joins CI. `df2a216` |
| 2026-09-12 | W5 | FE-5 | 0.7 | The panel's surface — **1.5 h planned, −0.8.** The design problem was making a null result read as a *measurement* rather than a missing feature, and three choices carry it: the denominator is in the headline (*"no flips detected"* is also what a broken harness produces); every trial is listed so the headline can be checked rather than taken; and the caveat carries the same weight as the claim, because a bold zero with a footnote is how a narrow measurement becomes a broad claim. No numeric literals in the file, same rule as FE-6. `df2a216` |
| 2026-09-12 | W5 | M2-6 | 1.7 | **Judge recall 8/10 (80%) against a ≥70% target — the first B4 criterion met on measurement rather than assumption**, after three that came back negative. **0 false flags over 24 steps in 5 unmutated traces**, which is what makes the 80% mean anything: a judge that flags freely catches seeded errors by accident. **The correct-step rule is the whole measurement, and SE-01 is why.** `875 + 50 = 925` was mutated to `= 935`; the judge returned `sound` at **0.95 confidence** with the rationale *"yielding 875+50=935 (correct)"* — it copied the wrong total, appended *correct*, and then flagged **three other steps**, sensing something wrong and blaming the wrong lines. A recall computed as "was the trace flagged anywhere" scores that as a hit. SE-05 is the same shape one layer up: a dropped `rounded down` constraint graded sound against the rule the step itself introduced. The patch is applied **after** segmentation so `step_id` cannot renumber — Hazard 1 through a side door. **1.5 planned, +0.2.** `77d369a` |
| 2026-09-12 | W5 | M2-18 | 0.7 | **ADR-012 (the thresholds ADR C10.3 calls `ADR-002-thresholds`; that number was taken in W2 by span emission, and two ADR-002s would make every cross-reference ambiguous).** Records every threshold with the data that chose it — and records that **the lever the misses support is not a confidence threshold**: both were high-confidence, so no floor separates them from the eight hits without escalating everything. The two levers the evidence does support are written down and deliberately **not implemented**, because fitting a prompt to ten cases is how a prompt gets fitted to ten cases. Also: **the error types are close to noise** — 2 of 8 named correctly, `arithmetic` applied to four including a unit conversion and a variable swap — so `error_type` must never render as a measured quantity, and B4 is recommended to stay without a criterion for it rather than invent a target at this n. `77d369a` |
| 2026-09-12 | W5 | FE-8 | 0.9 | **The SSE half has no consumer and is not built; the banners were always the valuable half.** C10.4 paired them because the plan assumed a hosted service streaming progress — ADR-003 deleted the service, so there is no process to stream from and M3-1b is already droppable. Seven run-level states render (failed arm, unannotated arm, provider-summarised, partial, escalation capped, budget bound, cached-only), **all seven exercised today by `report_degraded.json`** — which is exactly why G1 specified that fixture to carry five at once. Verified from the exported HTML, not from the build succeeding: 7 banners on the degraded fixture, exactly 1 on a real measured run. The rule they follow: **a banner names what is missing AND what is still true** — *"something went wrong"* makes a reader distrust the page; *"this arm failed, the other two are unaffected"* tells them how much to discount. **1.5 planned, −0.6.** `11e903f` |
| 2026-09-12 | W5 | FE-10 | 0.6 | **FE-10's claim is now enforced rather than asserted.** *"The featured comparison renders with the API unreachable"* is easy to claim and easy to break: one `useEffect` that fetches and the page still looks right in dev while shipping an empty shell, because in dev the backend is running. `make fe-export-check` reads the built artifact the way a reader with no network gets it — **every `<script>` stripped, then look for the words** — and refuses any `localhost` surviving in markup, since the export opens from `file://` in the fallback path where that is a blank section rather than a slow one. **2,193 characters of real text on the home page with every script removed.** 1.0 planned, −0.4. `11e903f` |
| 2026-09-12 | W5 | M3-5a | 1.1 | **Six operating procedures, each executed once before being written** — M3-5a's DoD, and not ceremony: a runbook written from the source describes what the author *believes* the commands do, and the gap is what an operator finds at the worst moment. **Two of the six failed on first run and both failures are in the runbook rather than quietly fixed**: `make smoke` came back 4 of 16 red with every failure real (so the entry says *do not treat a red smoke run as flaky — it has not yet produced a false alarm*), and `make wheel` failed on the unpackaged schema (so the entry says run it after touching `analyzer/`, not before a release). `e1a19e9` |
| 2026-09-12 | W5 | M3-9 | 0.8 | **G3's checklist executed in W5 rather than W12**, because the breakdown says three rows cannot close and one has no owner at all, and that discovering it on the last day *"converts a clean gate into an argument"*. **7 closed, 4 deleted by ADR-003, 5 open**, every open row with a named owner. Two deviations stated rather than smoothed over: **E2's live re-run is deleted scope, not missed scope** — what the criterion wanted (every degraded branch reachable) is built and rendered; the transport was the plan's assumption about how a reader would reach it, and at a gate that distinction is the difference between a decision and a shortfall. **E8 is half a measurement and is reported as half.** And E12/E13 need a human who is not the Lead: a tester who is also the author measures the author's memory of the design, and a peer dry-run by its author is a proofread. `e1a19e9` |
| 2026-09-12 | W5 | M2-11 | 1.2 | **The measurement workflow gated every job behind `if: false` — and a job that cannot run cannot rot visibly.** By W5 three things in it were wrong: the make targets, the artifact paths, and the secret, named **`ANTHROPIC_API_KEY`** — a provider ADR-001 ruled out in W1, surviving three weeks because nothing ever ran it. Jobs are now **enabled**, not corrected-and-disabled: `make calibrate` runs on zero labels by design, so the dev job runs today and reports *not yet measured*. The κ comment refuses a bare number (every figure carries n and interval), refuses to call *not yet measured* a failure (that trains reviewers to ignore it by the third PR), and refuses to invent a baseline. It upserts rather than appends. **`--final` stays manual and additionally refuses unless HEAD is at a `prompts-frozen` tag** — on any trigger, a workflow re-run silently becomes a second read of the sealed set and P3 stops being checkable. Fixed `lstrip("issuecomment")`, which strips a character SET, not a prefix. **1.5 planned, −0.3.** `307ecf0` |
| 2026-09-12 | W5 | M2-4 | 1.3 | **The full-corpus v0 pass — and it overturned ADR-010's headline.** One pass over 14 items x 3 arms at bundle `97667881c779` (49 analysis cassettes fell out of it). ADR-010 had published ***`backtracking` 0 in the whole corpus*** off **a single run of a non-deterministic classifier**; M1-9's reliability data re-ran that corpus **12 times / 3,579 rows** and `backtracking` is **2.0% (71 rows), firing 1-15 times per run**. Rare, not absent — and a run returning 0 sits comfortably inside that spread. **This is the mistake ADR-005 and ADR-006 each refused, committed by this project two ADRs later**; the error was the inference, not the arithmetic, and it cost nothing only because an unrelated DoD happened to re-run the corpus 12 times. What stands: **82.3% `linear`** (the majority-class baseline that makes B4 #2's 0.60 kappa target hard however good the classifier is) and `backward_chaining` at **0.2%**, 7 rows in 3,579, which puts B4 #2's *lowest per-class F1 >= 0.50* at risk on that class alone. 2.0% against the corpus-side **4.2% ceiling is consistent** — a stronger position than 0% was. `99ed473` |
| 2026-09-12 | W5 | M1-1 | 0.8 | **ADR-001's local-only promise, measured at last — and it labels everything `linear`.** "Can this run entirely on a laptop with no API access?" had been an **assumption for four weeks**: S3 probed the local tier directly, but nothing ever ran `ANALYZER_BACKEND=local` through `rlens.classify`, so a **supported configuration had never been exercised on its own code path**. It runs, and it is useless for this task. Same 6 traces / 64 steps: **100% `linear` (64 of 64)**, the other four classes **never once**, **0 unsound verdicts** vs 9.6% hybrid, 77% identical confidence pairs, 30% of steps below the 0.70 escalation floor. **Both halves of C4.3's merged call are inert** — kappa undefined for four of five classes, judge recall zero by construction. Local-only stays a supported *runtime*, but it is **not a supported measurement tier**, and that is now a published number rather than a hope. `fb22a1f` |
| 2026-09-12 | W5 | M1-9 | 0.8 | **DoD MET: 1 parse failure in 1,058 calls — 0.095% against a 2% bar.** Three attempts; twice the machine was the reason (a sleeping laptop killed attempt 1 at run 15, DNS killed attempt 2 at run 17). **23 runs recorded, 22 graded, 1 excluded as a network outage — and the exclusion rule was written before the number was seen**, fired by the harness itself. A reader insisting on strict consecutiveness has **17 runs / 767 calls / zero failures**; one accepting the exclusion has 22 / 1,058 / one. Both are in the record; neither changes the verdict. **The single failure is worth more than the 1,057 successes**: `mb-09.thinking` returned **26 rows for 25 steps** — an extra label for the first step of the *next* chunk, whose text it had because context travels with every chunk. Nothing was missing. The tempting instinct (an extra row is harmless, drop it) would have accepted **25 labels from a model that had stopped following its instruction** with nothing in the report saying so; the arm degraded and rendered unannotated instead. 95% CI **0.002%-0.53%**. `543fb68` |
| 2026-09-12 | W5 | M3-2b | 0.7 | **The cache is warm at the shipping pin — 14 reports, 0 stale — and the run exposed a trap that would have cost real spend.** Scanning staleness in a shell that had **not sourced `.env`** reported **14 of 14 stale on `model_pin`**: the process had computed a fingerprint over empty strings, so **an *unconfigured* pin was indistinguishable from a *changed* one**. The refusal then reads *re-warm the cache* when the repair is *load your environment* — and re-warming would have spent 14 items of analysis to fix a missing env var. `check_report` now uses the `unpinned_fields()` that already existed and says which it is. **That change broke three staleness tests, and the break was correct**: they had been running with no pin, exercising the unconfigured branch while claiming to test drift. G3 **E4 closed**. `5638271` |
| 2026-09-12 | W5 | M3-1a | 0.5 | **`make smoke` 18/18 green against a real server with `OPENAI_API_KEY` stripped — M3-1a's DoD met, G3 E1 closed.** The run found the live route **promising work it could not finish**: `--no-key` got a **202** back. Every read path was correctly green; the write path was not, and the reason is **the asymmetry ADR-001 created and nothing was checking — generation is local and needs no key, classification is OpenAI and does.** A keyless live run generates three traces perfectly well, spends the local compute, and fails at classification: halfway, with a half-built report and no warning. `analysis_ready()` now gates the route and `/readyz`, and the smoke check is tightened so that under `--no-key` **a 202 is a failure** — *guarded* has to mean refused up front, not refused eventually. 29 backend tests. `5638271` |
| 2026-09-12 | W5 | M1-14 | 0.5 | **G1 IS CLOSED AT 10/10.** The last box was cassette replay and it closed as a **by-product**: the pipeline passes a cassette name on every call rather than only in mock mode, so **49 analysis cassettes fell out of the warm-cache run**, and the recorded call is the production call on the same code path. **All 14 items x 3 arms now replay and validate with the socket broken** — `test_pipeline_mock.py` replaces the socket constructor, so a cassette miss is a hard failure rather than a silent live call, and a cassette recorded for a different request is refused. From here **CI's integration-mock job runs the entire bank with no LLM calls and local development is free** — three claims elsewhere in the plan had assumed this already existed since W5. Bundle `97667881c779`; these go stale and get re-recorded at M2-16's freeze, which the plan budgets. `b07bc7b` |
| 2026-09-12 | W5 | M3-9 | 0.3 | **G3 moves to 9 closed / 4 deleted / 3 open**, and **E8's cached half is now measured rather than floor-asserted**: p50 **0.9 ms**, p90 **1.0 ms**, p99 1.3 ms over **n = 140** requests across 14 items, against a 5,000 ms budget. **A number 4,800x inside its budget invites the wrong reading, so both caveats travel with it**: this is the server-side path over loopback, not what a viewer experiences, and it is fast **structurally** — C4.9 forbids a `GET` from triggering a model call, so nothing on this path *can* be slow. It is evidence the rule holds, not that the service is fast under load; nobody has put it under load and, with one operator, nobody will. **The live half stays `null` and is labelled not-applicable with its reason** rather than left as an empty cell that reads like an unfinished job. `b07bc7b` |
| 2026-09-12 | W5 | FE-2b | 0.5 | **"All fixture states render" is a DoD that passes by inspection on whichever trace you happen to be looking at** — a component rendering four of five behaviour classes looks correct on the class it is demoed with, and the fifth is found by whoever opens the one trace that has it. `make fe-export-check` now asserts **all ten states appear in the exported markup**: five behaviour classes, three validity verdicts, an unannotated step, a failed arm. **Note which fixture carries `backtracking`: the authored one.** ADR-010 had measured zero in the corpus, so a check built only on measured reports would have passed **while the class was unrenderable** — exactly the gap G1's authored fixture was committed to cover, and this is the first thing to consume it. **Greyscale legibility is a shape, not a tint**: sound has no rule, unsound a solid one, unverifiable a dashed one, so the three survive a photocopier. Both assertions **negative-tested** — removing the dashed border exits 1 and names the class that lost it. **2.0 planned, −1.5** (the renderer itself landed in FE-2a). `96c0f85` |
| 2026-09-13 | W5 | M2-14 | 1.2 | **The enriched half of the calibration frame comes up 31 of 60, and t13 fires.** Drawn from the 179 steps remaining after the random-90: `verification` **15 of 15** (25 candidates), `subgoal_setting` **15 of 15** (16), `backtracking` **1 of 15**, `backward_chaining` **0 of 15**. Enrichment **4.26×** on the non-linear classes. **Two consequences.** `dev-100` cannot hold 100 rows — C5.1 defines dev as random 1–40 + the enriched half, so it is **40 + 31 = 71**, and the G2 report quotes 71; a file named for a number it does not contain is the flattering artifact this project keeps refusing. And **B4 #2's *lowest per-class F1 ≥ 0.50* is now at risk on two classes** — `backward_chaining` undefined at n=0, `backtracking` near-undefined at n=1 — neither of which is a statement about the classifier. **The shortfall is partly the sampler.** These are ONE pass of a NON-DETERMINISTIC classifier, and ADR-010's amendment measured `backtracking` at 0 on one pass against 2.0% over twelve. A multi-pass union would find more candidates and was **deliberately not taken** — changing how the enriched half is selected is a change to the sampling frame, which is the reviewer's call, not the script's; recorded in `sampling.json` under `single_pass_caveat` so the choice is visible rather than implicit. Enrichment is from **v0, un-tuned, deliberately**, so the rare-class set is not coupled to the tuned model's own error structure. **Backfilling is refused in code**: `test_sampling.py` fails on overlap, on a class taking more than its candidates, on a dropped shortfall, and on t13 reading *not fired* while a class is short — **all five negative-tested**. `label.py --part enriched` serves the queue. P6 met; **P5 stays unticked** — the mapping no longer matches §2.2's `enr 60`. **0.5 planned, +0.7.** `de936cf` |
| 2026-09-13 | W5 | FE-9 | 1.4 | **The README's mount claim was not true, and the shipping build could not show a failure state.** `FRONTEND_OUT` was defined in `app.py` and **never read** while the README claimed *"`frontend/` is a static export mounted by the backend"* — the same defect class as `app.py` citing a `test_api.py` that did not exist. **Most of FE-9 is deleted scope, and it is E2's deletion again**: C10.4 wrote it against a hosted service (SSE ordering, reconnection, loading states), ADR-003 deleted the service, and the frontend reads its data at **build time**, so there is no runtime fetch to integrate. What survives is real — **one origin serves both the page and the API**, because the alternative (page on `file://`, API on `127.0.0.1`) makes every call cross-origin and invites CORS onto a backend whose whole posture is that it accepts almost nothing. Mounted **last** so it cannot shadow `/api`, only if the export exists so the API's tests never need the frontend toolchain, and `/readyz` reports `frontend_mounted` because the mount resolves at import time. **12 tests + 4 real-server smoke checks; `make smoke` 22/22 with the key stripped**; traversal asserted on *this* service over 7 parametrised attempts, each checked for leaked `.env`; **both load-bearing assertions negative-tested.** **THEN THE MEASURED BUILD FAILED `fe-export-check`, and that is the finding.** `['unannotated', 'arm failed']` render nowhere, because **the measured corpus is healthy** — 42 arms all succeeded — and measured mode was dropping the authored fixtures entirely. **The shipping demo could not show a degraded state at all**: FE-8's seven banners and FE-2b's ten trace states were unreachable in the only artifact a visitor sees. This is the exact mirror of FE-2b's own note — there, a check built only on measured reports would pass while a class was unrenderable; here, a *build* that keeps only measured reports renders a site that cannot show its own failure modes. **`report_degraded.json` was committed at G1 for precisely this** and dropping it threw away what the gate bought. Measured mode now keeps both (ids cannot collide, measured wins, `Provenance` is loud), and **measured sort first** — keying on id alone put `fx-01` above `mb-01`, burying fourteen real runs under three invented ones. Shipping export **21 pages, 17 item pages, all ten states**; fixture mode unchanged and still green. **1.5 planned, −0.1.** `babc2af` |
| 2026-09-14 | W5 | M2-2 | 0.4 | **Prep, not the task — the task needs Ankit.** `calibration/annotator-2.md`, the record the calibration README has listed as required since W4 and which did not exist: identity block, the signed confirmation the annotator worked from the rubric alone, and **the brief to send, verbatim**. **The brief is the point, because the failure mode for B4 #1 is not malice, it is helpfulness** — the instinct when handing someone a task is to explain the tricky cases, and the tricky cases are exactly what is being measured. So it also says what *not* to do: do not sit with them, do not answer *"is this verification or linear"*, do not show them any report page, do not fix the rubric mid-pass. A question the facilitator answers is a question the rubric failed to. Carries the ordering control where it will be read — **compute the IAA κ before the classifier's, and keep the commit order in git**, because an IAA κ computed afterwards is a number produced by someone who already knows what it needs to be — and the warning that appending a hard *case* to `rubric.md` is free while changing a *definition* bumps the bundle and invalidates every analysis cassette. `2b8a083` |
| 2026-09-14 | W5 | M3-5b | 0.4 | **Prep, not the task — the task needs five people.** `docs/walkthrough-notes.md`: protocol, facilitator script and the empty record. **Written before anyone is booked, deliberately** — deciding what counts as a pass *after* watching five people struggle is how a communication test becomes a post-hoc justification, so both targets are fixed in advance (5 of 5 unaided · ≥ 4 of 5 stating the insight **verbatim, not as a tick**). The script says to ask one question and then stop talking, and supplies the sentence for when a tester asks something — *"I'd rather not say"* — because **every answered question invalidates that tester's unaided result**. The three debrief questions deliberately exclude *"did you notice fluent reasoning can be unsound?"*, which is the answer being measured. And the refusal lives in the file rather than in memory: **fewer than 4 of 5 gets published and the demo ships — do not run a sixth tester**, that being the expired time box in a new costume. **Both files open with a stop block saying no result exists**; a sheet that looked measured because it was written early would be the exact failure this project's design refuses. `2b8a083` |
| 2026-09-14 | W5 | M2-19 | 0.4 | **DoD MET. The questions were answered; they were just never written down.** M2-19 assumes a Frontend owner asking a Lead, and amendment 001 made this solo — so there was no question queue, and a log of inter-person questions would have been a log of nothing. Same substitution the amendment already made for G1 check 10. `docs/frontend-questions.md` records **eight decisions** with their category and their cost-if-deferred, because a question answered in one head and never written down is indistinguishable at G3 from a question nobody asked. **THE HEADLINE IS WHAT G1 WAS BOUGHT FOR: `schema_version` NEVER MOVED.** Eight surfaces against the frozen `ReasoningReport` cost **one additive fixture extension and zero schema changes** — and the freeze is mechanical rather than a promise, since `schema_version` is a `const` and `additionalProperties: false` is set at every level, so a breaking change cannot happen without an edit visible in review. **One new gap found and deliberately NOT fixed**: `error_type` has five enum values and the fixtures exercise three. The renderer is type-agnostic so no per-type branch can break, and **ADR-012 found the types are close to noise (2 of 8 named correctly) and ruled `error_type` must never render as a measured quantity** — extending fixtures would buy coverage of a field the ADR says not to lean on. No open schema question carried into Month 3. **0.5 planned, −0.1.** `fa38206` |
| 2026-09-14 | W5 | M3-10 | 0.2 | **Closed with M2-19, same substitution and the same file.** M3-10 is the Month-3 half — *"same-day answers to FE-9's integration questions"* — and FE-9's one real integration question is item 8 in the log: **the README claimed the backend mounts the static export and `FRONTEND_OUT` was defined and never read.** Answered by building it (FE-9), not by replying to anyone. The DoD's second clause holds by construction: **any API change made in response was additive and G1-compatible** — the mount adds a route and touches no schema. **0.5 planned, −0.3.** `fa38206` |
| 2026-09-14 | W5 | M2-6 | 1.1 | **M2-6's last clause — *"Commit them"* — and the reports audit M2-6's own headline.** Ten mutated reports built, schema-validated and served from `/api/replay/{case_id}`. **A replay report is a third provenance category**: not an authored fixture (a real model produced these labels on the pinned tier) and not a clean measurement (the text was deliberately edited), so it never goes near `/api/report/{id}` — asserted by a test rather than left to the bank allowlist to happen to hold, with `illustrative` on the payload rather than the page because a report travels into a download, a cache and a screenshot. **BUILDING THEM MEANT RUNNING THE TEN CASES TWICE MORE, WHICH AUDITS THE ONE CRITERION THIS PROJECT HAS MET: recall 8/10, 8/10, 9/10. B4 #3 IS MET ON ALL THREE (80/80/90% against ≥70%)** and nothing here weakens that. What moves is *which* cases miss: **seven stable hits, one stable miss (SE-05 `dropped_constraint`, 0 for 3), and two unstable cases that are BOTH `arithmetic_slip`** — SE-01 miss→hit→hit, SE-03 hit→miss→hit. So ADR-012's `arithmetic_slip` cell has n=2 and has read **0/2, 1/2 and 2/2** across three honest runs. M2-6's DoD already demanded per-type cells as hit/miss with n stated — now measured rather than anticipated. **ADR-012 amended**: SE-01 was lever 1's worked example and the judge has since caught it twice unaided, so **lever 1 keeps its rationale and loses its evidence**; SE-05 survives, so lever 2 is the one with evidence. **TWO OF MY OWN CLAIMS WERE WRONG AND ARE CORRECTED RATHER THAN QUIETLY FIXED**: the docstring said these rebuild offline and `RECORD_CASSETTES` was never set, caught by actually running `REPLAY_MOCK=1`; and the two-run write-up said the aggregate *"reproduced exactly"* — run 3 returned 9. **Two points looked like a constant.** 10 replay cassettes committed, rebuild ~0s. `09e325a` |
| 2026-09-14 | W5 | FE-11 | 0.6 | **The replay half only — the G2-branch delta stays blocked** until M2-17 names the branch. Its precondition (*"the mutated reports committed in W7"*) had existed for about an hour. Under **L3** the replay is a **labeled bank entry, not a separate UI mode**: ten ordinary item routes keyed by case id, in the picker beside everything else, pre-rendered like every other page — **which is what makes it the surface that survives a provider outage** (C4.8), since there is no live call anywhere in it. **The banner is non-dismissible structurally rather than by setting**: plain markup, no handler, no button, because *"non-dismissible"* implemented as a state a reader can toggle is one bug away from being dismissed. It names the mutated step and the mutation type and says **whether the judge caught it — including when it did not**. **The metadata is kept OFF the report object on purpose**: `Download` promises the blob is *"the ReasoningReport itself, unmodified"* and the schema sets `additionalProperties: false` at every level, so a `__replay` marker on the report would have broken that promise and the download with it — the marker lives on the wrapper. Two export assertions, **both negative-tested**: the banner must appear in **script-free markup** (if it lived only in the JS payload a reader without JavaScript would get the trace and not the warning — the failure mode inverted), and it must have **no dismiss control**, checked as the absence of an affordance rather than the presence of a word. 31 pages, 27 item routes. **0.5 planned for this half, +0.1.** `2b19a83` |
| 2026-09-14 | W5 | M3-0 | 0.3 | **Two of §11's seven unblock rows are already dead.** §11 marks **D3** *"blocks M3-4"* and calls it the row where *"the critical path stops at a task no amount of code advances"* — true when Month 3 ended at a deployed service. **ADR-003 deleted the deployment**, so D3 and D4 have no account, region, IAM role, hostname or certificate to name; both recorded as **closed-by-decision rather than dropped silently**, because a reviewer who remembers §11 will look for them. **Four are open and none has a default**: five testers, a peer for the runbook dry-run, an owner for the lit-survey sign-off row that **has never had one** (*"it fails only by being forgotten, which is exactly how it will fail"*), and the C10.1 contingency. **U4's numbers have moved and the file says so**: §11's default reads *"C10.5's trigger already fired at G2"* — it fired earlier and by more, **91.5 h against a 12 h allocation** with L1/L2/L3/L4/L6 all applied, so the contingency and the calendar are the only instruments left. **D6 gets a recommendation rather than a silent default** — Langfuse was C9.1's only cost dashboard, but generation is local and free, nothing is deployed, and ADR-011 put the spend total in a file the breaker reads; recommend *superseded*, but that is the tech lead's call so it stays open with the reasoning attached. **And the file names the row §11 does not contain**, because §11 assumed the labelling had happened: **M1-11's 40 labels block nine tasks and a gate**, need no second person, and run ~65 min — the chain drawn out so the cost of deferring it is visible rather than asserted. `5bd0807` |
| 2026-09-14 | W5 | M1-11 | 0.2 | **Pre-flight on the 40 labels: is the session interruptible?** This project has **twice lost work to a harness that wrote its record only at the end** — M1-9's first attempt lost 13 runs to a sleeping laptop — and the 40 labels are the highest-value hour left and the worst thing to lose at minute 40. So the same failure mode was **checked rather than assumed**. It is not there: every label is appended and flushed on the keypress, an interrupt prints *"everything labelled so far is already written"*, and a second run skips what is done with no duplicates. **Proven by running the real `main()` against a redirected output directory** — three labels survived an abrupt kill mid-session and resume picked up cleanly — **with `calibration/labels/` untouched**, that being the corpus whose entire value is that a human wrote every row, and the reason `--dry-run` exists after a smoke test once wrote a fake label into it. **Consequence for the ask: it does not need to be one sitting**, recorded where somebody about to label will read it. `05a06a4` |
| 2026-09-15 | W5 | M1-11 | 1.1 | **DoD MET — the 40 dev labels exist and M1-11 closes**, four weeks after its W4 slot and as the last Month-1 task. Random-90 positions 1–40 in seeded order, both labels in one pass, no duplicates, no skips. **Hours are derived, not wall-clock, and that is deliberate**: rows 31–90 were judged first and entered in batches of ten, so `labeled_at` records the write and not the reading. The only clean rate sample is the 30 individually-stamped rows — **1.10 min/step median, 1.66 mean against the plan's 1.6** — and 40 × 1.66 is the 1.1 h booked here. The provenance pattern and the annotator's confirmation are recorded in `calibration/README.md` so a later auditor reads evidence rather than an alarm. `c7e070c` |
| 2026-09-15 | W5 | M2-1a | 1.4 | **DoD MET — the held-out 50, labelled in W5, the week the plan books them.** Positions 41–90 in seeded order, same blind tool, both labels. 50 × 1.66 min at the measured rate. **M2-1a's overrun trigger does NOT fire** — the naïve wall-clock reading of the file (3.1 h) would have fired it, and it would have been wrong: it is measuring batched entry, not labelling. **C10.3's 3.0 h labelling line is the first estimate in this project to survive contact with the thing it estimated.** `c7e070c` |
| 2026-09-15 | W5 | M2-1a | 0.8 | **The pass's own outputs, which are not the labels.** (1) The two files the plan names — `dev-100.jsonl` at 40 and `heldout-50.jsonl` at 50 — split out of the single `<annotator>.jsonl` the tool actually wrote, verified as a partition with no row rewritten. (2) `calibration/adjudication-queue.md`: **the 14 rubric questions the pass could not answer**, each with the reading actually applied, the step ids, and the labels a reversal would invalidate. **None was resolved mid-pass** — M1-11's own rule, and the reason v1's 90 labels are internally consistent even where they may be wrong. It is M2-2's agenda and it **must never be sent to the second annotator**, being the author's reasoning about exactly the cases being measured. (3) The provenance record above. `c7e070c` |
| 2026-09-15 | W5 | M2-13 | 0.9 | **C5.4's held-out guard was keyed on a FILENAME, and the labelling exposed it.** `make calibrate`'s default — what M2-3's loop runs every cycle — excluded `heldout-50.jsonl` by name and nothing else, while the tool writes `<annotator>.jsonl`; so both halves sat in one file and **every dev number would have silently included the 50 steps the published claim depends on never being tuned against**. **The same hole was waiting for W6 no matter how the labelling had gone**: `annotator-2.md` sends Ankit to `labels/<annotator>.jsonl` and he labels *nothing but* the held-out 50. Now keyed on the draw (`sampling.json`'s random-90, split at 40) with the filename rule kept as a redundant second check, and `label.py` gets `--part {dev,heldout,enriched}` so a pass cannot walk across the boundary on its own — which is how these two ran together. **Two regression tests, both watched to FAIL before being trusted to pass.** Then the first real `make calibrate`: **soundness κ 0.761, behavior κ 0.126** — findings 11 and 12. 421 tests green. `c7e070c` |

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 6.7 | **+3.4** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of amendment work, **1.4 h of W2 work pulled forward** (M1-15 + M1-16) and **0.5 h unbudgeted** (the tokenizer for G0 check 2). See the like-for-like note below |
| W2 | 6.7 | **8.9** | **+2.2** | **Complete.** M1-15, M1-16, M1-2, M1-6, M1-4 all done. 1.4 h of it was delivered in W1 |
| W3 | 7.5 | **18.6** | **+11.1** | **COMPLETE.** M1-5 6.4/1.5 · M1-7 5.3/3.0 · M1-8 5.0/2.0 · S3 1.9/1.0. `segmenter-frozen-v1` tagged. The heaviest week on the plan ran 2.5x its budget |
| W4 | 8.0 | **15.5 to date** | | M1-9 4.5/3.0 · M1-10 4.9/1.5 · M1-11 2.6/2.0 (tooling; labels are not the Lead's to fabricate) · M1-13 2.1/1.0 · M1-14 0.7/0.5 · M1-1 0.7. **M1-13 is the first task to give hours back** — ADR-009 re-scopes M2-9 from 3.5 h to ~1.0 h |
| **Total** | **26.4** *(25.5 + M1-2 0.6 + M1-6 0.9 − M1-4 rounding)* | **48.3** | **+21.9** | **Month 1 closed at 48.3 h against 26.4 planned and 12.0 allocated**, and W5 has since carried **5.3 h more of Month-1 work** — M1-9's DoD, ADR-001's local-only measurement, M1-14's cassettes, ADR-010's amendment and **M1-11's 40 labels (1.1)** — for a **Month-1 task total of 53.6 h**. **No Month-1 task remains open** |
| *vs. C10.2 Realistic* | 22.0 | | | *+3.0 = the four §1.3 gaps, less L1/L2* |
| *vs. Lead capacity* | 12.0 | | | *the C10.1 bet, first reading at end W4* |

## Month-2 planned-vs-actual

Month 2 is W5–W8. **W5 started before Month 1 finished**, which is a statement about
sequencing rather than about discipline: M1-9's DoD measurement is compute, not keystrokes,
and M1-11's 40 labels are not the Lead's to fabricate. Both are named below rather than
quietly carried.

| Week | Planned (breakdown) | Actual | Δ | Notes |
| ---- | ---- | ---- | ---- | ------ |
| W5 | 9.0 | **47.9 to date** | **+38.9** | **M1-11 + M2-1a — the 90 labels, 3.3 h** · M2-13 3.2/1.5 · FE-1 3.2/1.5 · FE-2a 1.4/2.0 · FE-3+FE-4 1.8/3.5 · FE-6 1.2/1.0 · FE-7 0.4/0.5 · M2-5 2.1/2.0 *(part)* · M2-8 1.6/3.0 *(part)* · **M2-4 2.0/2.0 — prep 0.7 + the full-corpus pass 1.3**. **The week splits 19.5 M2 · 12.7 FE · 10.2 M3 · 5.5 M1**, and only the first two are this month's work. M1 spill: ADR-010 + its amendment 1.3, M1-9's harness fixes 0.6 and its DoD 0.8, ADR-001's local-only measurement 0.8, M1-14's cassettes 0.5, the labelling guard 0.2, **M1-11's 40 labels 1.1**. M3 pulled forward: the backend tier (M3-1a 1.9, M3-3 2.2, M3-2a 0.9, M3-7 0.6), M3-8 0.8, M3-5a 1.1, M3-9 1.1, M3-2b 0.7 |
| **Month 2 total** | **~34** | **47.9 to date** | | **W5 alone has now outrun the whole month's plan by 5.3x.** **15.7 h of the 47.9 is Month-1 and Month-3 work** carried here rather than hidden — Month 2's own share is 32.2 h against a 9.0 h week. **M2-1a is the first Month-2 task to land inside its estimate** |

> **Six of the eight frontend surfaces came in 1.9 h *under* their combined estimate**, and
> that is the first sustained underrun in this project. The reason is worth writing down
> because it was bought deliberately: they render a **frozen** object against **committed
> fixtures**, so every one of them was built without a running backend, without a model, and
> without a single question that needed an answer from somewhere else. That is precisely
> what G1 was for. The gate cost W4 dearly and W5 is where it pays back.

### Month 1 is closed — the last task landed 15 Sep

| Task | State | What it needs |
| --- | --- | --- |
| ~~**M1-9**~~ | ✅ **DoD MET 12 Sep** | **1 parse failure in 1,058 calls — 0.095%** against a 2% bar, over 22 graded runs. Took three attempts; twice the machine was the reason. See [`docs/spikes/M1-9-reliability.md`](spikes/M1-9-reliability.md) |
| ~~**M1-11**~~ | ✅ **DoD MET 15 Sep** | 40 labels in seeded order, both labels in one pass, blind tool. **And it answered the question ADR-010's amendment left open**: nothing in the classifier's own output said whether its 2.0% `backtracking` was the *right* 2.0%. A human read those steps, and the answer is that the behavior half of the classifier agrees with a human **less often than a constant would** — κ 0.126 against a 0.850 majority baseline. **The soundness half, which nobody was worried about, clears B4 #2 at κ 0.761.** Findings [11 and 12](findings.md) |

**Month 1 ran 09 Sep – 15 Sep on the calendar and 53.6 h on the clock, against 26.4 planned
and 12.0 allocated.** The last task was the one that could not be bought with hours: it
needed a human to read 40 reasoning steps, and it sat blocked for four weeks while
everything downstream of it waited.

> **⚠️ W1 is +2.9 over, and the raw number overstates it.** Read it in three parts.
>
> **1.4 h of the overrun is W2 work, not W1 overrun.** M1-15 (local runtime) and M1-16 (S6)
> are W2-0 tasks. They were pulled forward because M1-1 — a W1 task carrying the G0
> decision — was blocked on the model being served, and the plan's own W1 rule bars starting
> bank items, runner code or the segmenter. So the alternative was an idle week, not a
> cheaper one. Against their 1.0 h plan they cost 1.4 h.
>
> **1.2 h is the amendment**, already reported last entry: work that existed only because
> three constraints surfaced on day 2 rather than at kickoff.
>
> **0.5 h is unbudgeted work the plan never scoped:** closing G0 check 2. The gate asks for
> reasoning tokens counted *exactly*; the runtime reports none and bundles reasoning with
> the answer, so the split needed a tokenizer dependency (`tiktoken`, `o200k_harmony`) that
> Month 1 did not budget. The alternative was publishing cost-of-thought as an estimate all
> the way to G2, so it was bought now rather than deferred. It returns a real number — 741
> reasoning tokens, **73.4% of output** — and it reconciles against the runtime's own
> billing to +10 structural tokens, which is what makes it evidence rather than a plausible
> figure.
>
> **Like-for-like, W1's own tasks came in at 4.1 h against 3.3 h planned — +0.8**, and 0.5 of
> that +0.8 is the tokenizer. W1 execution excluding unbudgeted scope was +0.3.
>
> **The unflattering half.** The 0.3 h overrun on M1-15 was two defects in a script written
> the day before, both found only by running it for real: a truncated digest recorded as the
> pin, and an unquoted value that corrupted itself when `.env` was sourced. Both were in code
> that had been reviewed and committed. That is the argument for running a spike end-to-end
> rather than declaring the harness done — and it is a small preview of what W3's heavier
> weeks will find.
>
> **W2 is now 5.7 h against a 6.7 h plan**, and it still holds S2, the runner and the bank.
> The first reading that means anything is still **end of W4**.

---

## W2 — S2 landed, and it changed M1-6's shape before M1-6 was written

**M1-2 cost 2.1 h against 1.5 h planned, +0.6.** Where the overrun went, in order of size:

| | Hrs | Budgeted? |
| --- | --- | --- |
| Harness, stock agent, capture, delta table | ~1.1 | yes |
| **ADR-002** — the finding contradicts C3.1 | ~0.4 | **in scope, not in the estimate**: breakdown §4.1 says a contradiction with C3.1 "is a plan amendment that goes in an ADR, not a silent code fix" |
| **The control probe** — same request, raw HTTP, no LangChain | ~0.3 | **no** |
| Probe defect: re-specify the SKU and re-run | ~0.15 | no |
| `test_third_party_spans.py` — 5 contract tests guarding the capture | ~0.15 | no |

**The 0.3 h control was the most valuable 0.3 h in the task.** Without it the finding is
"reasoning is missing from the spans", which has three possible causes — the runtime, the
LangChain adapter, the instrumentor — needing three different fixes, one of which would
put ADR-001's whole local-generation decision back in question. The control issues the
identical request over raw HTTP, gets 173 chars of reasoning back, and narrows it to the
adapter. **A named cause is a half-hour fix; an unnamed one is a week of W3.**

**The unflattering part is the probe defect.** The first probe asked the model to look up a
price without saying which SKU. The model reasonably asked a clarifying question, never
called the tool, no TOOL span was emitted, and the delta duly reported the tool rows as
*absent* — a wrong finding, in a document whose only purpose is to be a correct finding.
It was caught only because **S6 had already measured this model at 20/20 on tool calls**, so
"this model does not call tools" was visibly false. Absent that prior spike it would have
shipped. An unexercised path reads exactly like a missing one, and nothing in the harness
distinguished them. It does now.

### Effect on the remaining W2 estimate — recorded this week, per breakdown §4.3

§4.3 asked whether S2 grows M1-6. **Both directions, and they nearly cancel:**

| | |
| --- | --- |
| Ingest half | **cheaper than 2.5 h** — five `gen_ai.*` precedence chains collapse to a single candidate each, and two branches (`tool.parameters`, span events) are deleted before being written |
| Emission half | **+0.5 h** — the runner must emit `llm.output_messages.0.message.reasoning` itself (ADR-002) |

**M1-6 is carried at 3.0 h (2.5 + 0.5).** W3 does not compress. W2 now stands at 3.5 h
spent with 3.2 h remaining against a 6.7 h plan — but that plan already absorbed 1.4 h into
W1, so W2's real remaining load is M1-6 (3.0) and M1-4 (1.7) = **4.7 h, not 3.2**. The
month total moves to **26.0 h** (was 25.5: M1-2 +0.6, M1-6 +0.5, less 0.6 of M1-6 ingest
saving not yet bankable until the code is written).

> **This is the ordering rule paying for itself, and it is worth saying plainly.** §4.1
> made S2 a precondition of M1-6 on the argument that writing ingest first means "three
> fallback branches, two of which are dead code, and discovering in W3 that the live
> attribute is a fourth name nobody listed." What actually happened is worse than the
> prediction: **five** rows were dead, and the load-bearing attribute is not a fourth name
> — it does not exist. Had M1-6 gone first, W3 would have opened with a rewrite of the
> ingest layer *and* an unresolved I1 question. The 2.1 h bought that.

---

## W2 — M1-6 at 3.4 h, and the arm-1 finding that changes what the project can claim

**M1-6 cost 3.4 h against the 3.0 h this ledger revised it to last entry (+0.4), and 2.5 h
as originally planned (+0.9).** The revision held up: the ingest savings S2 bought were
real, and the +0.5 emission estimate was close. The extra 0.4 is one thing.

### The 0.4: arm 1 was not doing what the plan says it does

C4.1 defines arm 1 as *thinking **off***. The first end-to-end run returned a direct arm
with **467 reasoning tokens**. The system prompt had done its job — the visible answer was
two tokens — and the model had reasoned anyway, invisibly and on the bill.

Four ways of asking `gpt-oss:20b` to stop, all measured on one prompt:

| Request | Reasoning returned |
| --- | --- |
| Omit `reasoning_effort` — *what "thinking off" plainly means* | 2918 chars *(the default, and near arm 2's)* |
| `reasoning_effort: "none"` | **2918 chars — silently ignored** |
| ollama native `"think": false` | **2918 chars — silently ignored** |
| `reasoning_effort: "low"` | **131 chars — honoured** |

**Two switches that claim to disable thinking do not error, do not warn, and hand back a
full trace.** Had the runner sent `think: false` and trusted it, the project would have
published a "no-thinking baseline" that thought 2918 characters, and every cost-of-thought
ratio in the study would have been wrong with nothing visibly broken. ADR-004 records the
decision: arm 1 requests `low`, is renamed a **minimal**-reasoning baseline everywhere, and
the separation is checked **from the token counts, never from the request** — because the
request demonstrably is not evidence. The probe now measures 144 vs 1453 tokens.

**This is the third time in two weeks that the same failure shape has appeared**, and it is
worth naming rather than logging three times. S1 refused to report "thinking text: present"
and gated G0 on a ratio. S2's first probe reported tool attributes absent when they were
merely never exercised. Now two provider flags accept a request and ignore it. In each case
the *request* or the *presence of something* looked like evidence and was not. The standing
lesson: **assert on the output, at a threshold, or do not claim the measurement.** It is
cheap to build in and it has now caught three real errors.

### A result on day one, and a new requirement it puts on M1-4

At `low` effort arm 1 answers the probe **18694**; the correct answer is **18678**, which
arm 2 gets. That is the study working — the prompt does not induce sloppiness, the reduced
budget costs accuracy on a multi-step chain.

But **if every bank item separates the arms this cleanly, the bank measures difficulty, not
strategy.** The `easy` floor is what should show arm 1 matching arm 2 at a fraction of the
cost, and that contrast is the finding. This is now a requirement on M1-4, not a nicety.

### Where W2 stands

**6.9 h spent against a 6.7 h plan, with M1-4 (1.7 h) still to go** — so W2 lands around
**8.6 h, +1.9**. Month-1 total moves to **26.4 h** against 12 h of Lead capacity.

**The contingency signal is now worth reading, three weeks early.** C10.1's bet was ~25 h
of work against ~12 h of allocation, first read at end W4. Two weeks in, the trend is not
that tasks are being estimated badly — the like-for-like execution has been close. It is
that **every spike so far has found something the plan did not know**, and each finding has
cost 0.4–0.6 h to write down properly. That is the spikes doing their job, and it is also
the strongest argument yet that the L1/L2 cuts taken at kickoff were not enough. **G2 should
expect to see the Option-2 contingency drawn on.**

---

## W2 closed — 8.9 h against 6.7, and the bank now spans both shapes of result

**M1-4 cost 2.0 h against 1.7 planned (+0.3).** 0.15 of that is a boundary-test rewrite
that was not M1-4's work at all (below); the rest is the checker module, which the
estimate did not anticipate needing.

**Checkers went into `rlens.checkers`, not into the test.** A bank whose answers are
validated by one implementation and graded by another is validated against nothing, and
`metrics.py` will need exactly these functions for accuracy. The test then asserts the
DoD's *mirror image*, which is the half that actually bites: every checker must **reject**
a plausible wrong answer. "Every checker accepts its own answer" is satisfied by a checker
that accepts everything.

### ADR-004's control group is real, and it was worth checking on day one

The `easy` items existed on paper as a hedge. Run for real:

| Item | Arm 1 (`low`) | Arm 2 (`medium`) | |
| --- | --- | --- | --- |
| `mb-01` (easy) | **K — correct**, 5 reasoning tokens | **K — correct**, 21 tokens | same answer, **4× cheaper** |
| multi-step probe | 18694 — **wrong**, 144 tokens | 18678 — correct, 1453 tokens | thinking buys the answer |

**That contrast is the product.** One row where deliberation is wasted spend and one where
it is the difference between right and wrong is exactly the claim B4 #7 wants to make, and
until this run the bank could only have produced the second row. A bank of nothing but
hard items would have measured difficulty and called it strategy.

### Two hazards written down now, because W3 is where they would cost

1. **The CRT traps may be memorised.** `mb-12/13/14` are cognitive-reflection archetypes
   with rewritten surfaces (notebook/pen, printers/posters, algae/pond). A 20B model has
   very likely seen all three, and a model that answers them correctly *from memory* is not
   a trap that failed to fire — it is a trap that was never tested. **Four traps are
   declared against a floor of three**, and `mb-11` is deliberately archetype-free as the
   hedge. If the CRT three miss M1-5's 3/5, the fix is more `mb-11`-shaped candidates, not
   a lower threshold.
2. **The lookup items use invented place names on purpose.** A lookup item about a real
   city measures whether the model already knows the answer; the tool never gets called and
   `tool_required` becomes a label for something that did not happen. `test_bank_answers.py`
   cannot detect that — only M1-7's arm-3 runs can — so the four required facts are
   specified in the bank README rather than left for M1-7 to infer.

### The boundary test was wrong, and the way it was wrong matters

The I1 import check grepped source text for `import problem_bank`. It flagged
`checkers.py`, whose docstring *discusses* that import precisely because it is forbidden.
It now parses the AST, and has its own test proving it still catches a real import and no
longer catches prose.

Worth the 0.15 h: **a false positive in a boundary test is not harmless.** I1 is the
invariant the architecture rests on, and a check that cries wolf is a check that someone
eventually relaxes. This is the second time in two weeks that a *detector* rather than the
code under test turned out to be the defect — the first was S2's probe reporting
unexercised tool rows as absent.

### Capacity, at the two-week mark

**14.2 h spent of a 26.4 h month, against 12 h of Lead allocation.** W2 ran +2.2 over.

The pattern is now stable enough to name: **like-for-like execution is close to estimate,
and every overrun has been a finding that needed writing down** — the tokenizer (0.5), S2's
namespace and reasoning-loss deltas with ADR-002 (0.6), arm 1's un-disableable thinking with
ADR-004 (0.4), the bank's checker module and the boundary fix (0.3). That is 1.8 h of the
2.9 h total overrun, and none of it is rework.

**This is the spikes working as designed, and it is also the C10.1 bet losing.** W3 is the
heaviest week on the plan (7.5 h) and holds M1-5, M1-7 and the segmenter freeze — the two
tasks that inherit the hazards above, plus the one task where a mistake invalidates every
label written after it. **G2 should expect the Option-2 contingency to be drawn on**, and
the honest read at W4 will be a month around 27 h against 12 h allocated.

## W3 — M1-5 at 5.0 h against 1.5, and a trap floor the model will not cooperate with

### The hazard M1-4 wrote down fired, and then the fix for it failed too

M1-4 predicted this: `mb-12`/`mb-13`/`mb-14` are famous cognitive-reflection archetypes
and a 20B model has very likely memorised them; `mb-11` was the archetype-free hedge. All
four reproduced **0 of 5**.

The plan's stop rule is unambiguous — *"this is a content problem, not a code problem —
author more candidates. It is not a reason to lower the threshold"* — so twelve more were
authored. Round 1 took the single-omission arithmetic mis-step: weighted mean, compounding
discounts, cuts-vs-pieces, percentage base change, two-phase fill rate, harmonic mean.
**36 runs, 36 correct.** Round 2 abandoned word-problem arithmetic entirely for the places
a 20B actually slips: three-set inclusion–exclusion, constrained combinatorics, quarterly
compounding, work-rate with a departure, a boundary off-by-one, mean after removal.
**36 runs, 35 correct, 0 traps.**

**120 runs, 16 candidates, one trap hit** — and that one did not fire in the pinned regime,
so even at 3/5 it would not have been demo-safe.

### The finding is ADR-004's second consequence, and it is the expensive one

ADR-004 established that thinking cannot be switched off on this model: `reasoning_effort:
"none"` and native `think: false` are both silently ignored, and `low` is the floor. The
trap premise assumed arm 1 would reason shallowly enough to take an attractive wrong turn.
**At `low` it still produces a real chain, and that chain solves every misdirection we
could construct.** There is no shallow regime here to trap.

What the arms *can* be separated by is **difficulty** — already verified on real runs in
W2: arm 1 wrong at 144 reasoning tokens where arm 2 is right at 1453, and `mb-01` correct
on both at 5 vs 21. Which is precisely the collapse ADR-004's note on the `easy` items
warned about: *"if every item separates the arms that cleanly, the bank measures
DIFFICULTY, not strategy."*

The **cost-of-thought** half of B4 #7 is untouched — it is a token-count claim and both
separations hold. It is the *accuracy* half that has lost its most photogenic instrument,
and **B6.3's wow moment now rests on M2-9 (cue injection) alone.** That makes S4 (M1-13,
W4) less slippable than C1.2's "safe to slip" list implies, and it is worth saying so four
weeks before anyone would otherwise notice.

### "Three of five runs" is not purchasable at the committed pin

The DoD asks for a hit count out of five. The pin is `GEN_TEMPERATURE=0` with a fixed
`GEN_SEED`, and `llm.generate` sends both for **both** arms — two thinking-arm runs of
`mb-13` came back byte-identical, 259 reasoning tokens each. Five runs there are one run
five times, and the count can only be 0 or 5.

So the measurement carries two regimes, and they answer different questions: **pinned**
(the demo's own greedy-decoded configuration — will it fire on stage?) and **sampled**
(temperature 1.0, five declared seeds — how fragile is that binary?). A tag is earned only
by clearing both on the same arm. **This is where the +1.1 h went**, and it was worth it:
a 3/5 measured at the wrong temperature would have been a number with no variance in it,
published as if it meant something.

### Two grading defects, and the same shape as the last three findings

Neither is about traps. Both were found only because M1-5 is the first task that grades
real model output against declared answers.

1. **`exact` scored 37.5% of correct answers wrong.** The arms ask for "the final answer
   on its own last line"; the model answers `7 minutes`, and a string compare against `7`
   calls that wrong. **18 of the first 48 runs.** `test_bank_answers.py` is structurally
   blind to it — it feeds each declared answer back into its own checker, and a string
   trivially equals itself, so the answers a model actually writes never appear in it.
2. **The answer extractor returned `\]`.** `mb-11`'s thinking arm closed with a LaTeX
   display block, so "the last non-empty line" was the closing delimiter. Skipping
   trailing decoration reaches the line above — which carries four numbers, so the honest
   outcome is **`unparsed`**, not wrong. A grader willing to pick the right number out of
   a worked line would pick the right one out of a *wrong* worked line just as happily.

> **This is the fourth time in three weeks that the DETECTOR rather than the code under
> test was the defect** — after S2's probe reporting unexercised tool rows as absent, the
> I1 import check flagging prose, and arm 1's un-disableable thinking. The pattern is now
> worth naming as a practice: **every measuring instrument in this project gets a test
> that feeds it something it should reject.** `test_checkers.py` is that test for the
> grader, and it is the reason the bank's own contract test is no longer the only thing
> standing between a wrong number and a published report.

Left unfixed, defect 1 alone would have understated accuracy by roughly 37 points on
`exact` items for the rest of the project, surfacing in M3 as "the model is worse than
expected" — the exact failure `test_bank_answers.py`'s docstring predicts and could not
catch.

### Capacity, at the three-week mark

**19.2 h spent of a 26.4 h month, against 12 h of Lead allocation.** M1-5 ran **5.0
against 1.5**, the largest single overrun of the project so far.

The like-for-like read still holds and is worth separating out: the trap measurement
proper — harness, 120 runs, log — was **2.6 h against 1.5**, and the over there is the
two-regime design the DoD's own wording forced. The other **2.4 h is two grading defects
and an ADR**, none of which is trap work and none of which is rework.

**The C10.1 bet is now clearly lost, not arguably.** W3 still holds M1-7 (3.0) and M1-8
(2.0) plus S3 (1.0), so W3 alone will land near 11 h against a nominal 3. **G2 should
expect the Option-2 contingency to be drawn on**, and the honest W4 projection is now a
month around **28 h against 12 h allocated**.

M1-8 is next and is the one to protect: the breakdown says so explicitly (*"protect M1-8
over M1-5, because M1-8 blocks G1 and M1-5 does not"*), and it is the task where a mistake
invalidates every label written after it. **M1-8 should read ADR-005's closing note before
freezing** — C4.2 already requires the segmenter to treat `\[ … \]` as one sentence and
never split inside a fence, and `_DECORATION` in `rlens/runner/run.py` is now the list of
delimiters actually observed in practice.

### Postscript — accepting ADR-005 falsified half of it, and that is the most useful hour of the week

Option B was accepted: withdraw the trap floor, re-point FE-1 at the difficulty contrast.
The first half was right. The second half rested on **one ad-hoc probe** — M1-4's control
run, arm 1 wrong at 144 tokens where arm 2 was right at 1453 — and no bank item had ever
been observed doing that.

So it was measured before being implemented: **14 items x 2 arms, then 5 harder candidates
x 2 arms. Zero separations.** Eleven items agreed; the three failures are `tool_required`
items run without tools, which is arm 3's job and not an arm finding.

**The cause is worth the hour on its own.** Arm 1's `low` effort is *adaptive*:

| Item | Arm 1 | Arm 2 | Ratio |
| --- | --- | --- | --- |
| `mb-03` (easy, factual) | 3 | 40 | 0.07 |
| `mb-13` (multi_step, logic) | 37 | 259 | 0.14 |
| `mb-06` (multi_step, arithmetic) | 169 | 206 | **0.82** |
| `hm-02` (7-figure successive percentages) | **407** | 423 | **0.96** |

The ratio climbs with difficulty. Arm 1 does not reason *less* — it reasons **as much as it
needs to**, invisibly, at the same price. So the harder the item, the *less* the arms
differ, in accuracy and in cost. `reasoning_effort: "low"` caps the style, not the budget.

**This is the same mistaken assumption that sank the traps, and it sank the fallback too:**
that arm 1 reasons less and therefore fails sooner. Two ADRs now rest on it. Had the
difficulty contrast been implemented on the probe's authority, FE-1 would have been
specified in W5 around a row that does not exist in the corpus — discovered by whoever
built the page, in Month 2, against a frozen contract.

**Generalising from one probe is the error here, and it was mine.** The probe was real; the
inference from it was not measured. The practice that follows is the same one the detector
findings keep pointing at: *a number that will be built on gets measured across the corpus
it will be drawn from, not on the example that suggested it.*

What survives is a genuine result, and a sharper one than the plan expected: **deliberation
cost up to 13x more reasoning tokens and changed the answer on none of sixteen problems.**
For an instrument built to make reasoning measurable rather than impressive, that is a
finding. The accuracy row FE-1 still needs is the **tool** contrast — `mb-08`/`mb-09`/
`mb-10` wrong on both reasoning arms and, if M1-7 works, right on arm 3. **That is the next
task**, which is convenient: it is also the one on the critical path.

## W3 — M1-7 at 5.3 h against 3.0, and the arm comparison finally has a result

### The probe that decided the implementation, before a line of it was written

C4.1 says *"LangGraph ReAct loop"*. S2 had already established that
`langchain_openai.ChatOpenAI` drops the runtime's `reasoning` field — that finding is what
ADR-002 exists to work around for arms 1 and 2. So one thing needed checking first: **where
does the thought text live on a tool-calling turn?**

| Field | Length |
| --- | --- |
| `content` | **0 chars** |
| `reasoning` | 86 chars — `'We need to look up the population of Fairhaven. Use lookup tool…'` |

The visible content is **empty** and the entire thought is in the field LangChain discards.
C4.2 defines ReAct segmentation as *"the thought text preceding each TOOL span becomes one
`thought` step"* — so a LangGraph arm 3 would have emitted a structurally perfect ReAct
trace with **every thought step blank**, and nothing would have looked broken. ADR-007.

B12's evidence is untouched: *the analyzer* must ingest a stock LangGraph trace, and
`test_third_party_spans.py` does exactly that and stays green. Arm 3's TOOL spans use the
attribute names read off that same capture — `tool.name`, `input.value`, `output.value` —
so C4.2 gets **one** ReAct code path rather than one for us and one for everyone else.

### The arm comparison has a result, and it is not the one the plan expected

| | Arm 1 (minimal) | Arm 2 (thinking) | **Arm 3 (ReAct)** |
| --- | --- | --- | --- |
| Correct, 14 items | 11/14 | 11/14 | **14/14** |

ADR-006 predicted the only accuracy separation in this bank would be **tools**, and said so
as a claim needing confirmation. It confirms: `mb-08`, `mb-09` and `mb-10` are wrong on both
reasoning arms and right on arm 3. **And arm 3 is cheaper doing it:**

| Item | Arm 2 | Arm 3 | |
| --- | --- | --- | --- |
| `mb-08` | unparsed, **3,966** reasoning tok | correct, **80** tok | 50× |
| `mb-09` | wrong, 1,568 | correct, 38 | 41× |
| `mb-10` | wrong, 847 | correct, 36 | 24× |

> On `mb-08` the thinking arm spent **3,966 reasoning tokens failing to recall a population
> that does not exist.** Every place name in the corpus is invented — M1-4 wrote that down
> as a hazard about `tool_required` being a label for something that did not happen, and it
> has now paid for itself twice: a real city would have been answered from memory and there
> would have been nothing to see. **That pair is the product in one frame:** one reasoning
> panel showing confabulation at length, beside one showing two tool calls and eighty
> tokens.

This is a better demo row than the difficulty contrast the plan wanted, and unlike that one
it exists in the corpus. B4 #7's wording is now specific and both halves are measured:
**tools buy the answer; thinking buys cost.**

### A silent-failure path worth more than the half hour it cost

`problem-bank/corpus/facts.json` was resolved relative to the working directory. That works
from the repo root, which is where the CLI is always run, and the first test that ran from
`analyzer/` found it.

**The interesting part is how it would have failed in production.** A missing corpus raises
inside a tool call — and the ReAct loop is *designed* to swallow tool exceptions into
observations, because that is what lets a model recover from a bad call. So from any other
directory, arm 3 would have run, called `lookup`, received `no fact corpus at
problem-bank/corpus/facts.json` as a perfectly well-formed observation, reported it
honestly, and answered wrong — **a green run, with a plausible chain explaining why the
fact could not be found.** `runner/paths.py` now resolves env → cwd → checkout and names
every place it looked; the corpus being absent is raised as the configuration failure it is,
before a turn is spent. `load_item` had the same latent bug and is fixed alongside.

### The third tag to turn out to be a claim

**2 of the 5 items tagged `tool_required` had arm 3 call no tool at all** — `mb-06` and
`mb-07`, both arithmetic — and answered correctly regardless. `problem-bank/README.md` says
the tag floors are *"what make B4 #7's `tool_required` share computable"*; a share computed
from the tag is wrong by two of five.

`is_trap` claimed 4 and earned 0. `tool_required` claims 5 and measures 3. **The rule this
bank has earned: a tag is a hypothesis until a run confirms it** — recorded rather than
relabelled, because dropping a tag changes an L1 floor and that is a scope decision.

### Capacity, and the honest W3 projection

**25.9 h spent of a 26.4 h month, against 12 h of Lead allocation — with M1-8 and S3 still
to run.** W3 alone is at 11.7 against 7.5, and M1-5 plus M1-7 have between them absorbed
more hours than any two tasks so far.

The like-for-like read still holds and still matters: M1-7's loop, tools, corpus and
emission came in at **3.4 against 3.0**. The other 1.9 h is the three-arm contrast
measurement, a silent-failure defect, and 52 tests. None of it is rework, and the contrast
measurement is the one that closed a headline claim.

**The month will land near 29-30 h against 12 allocated.** G2 should expect the Option-2
contingency to be drawn on, and that projection has been stable and rising for three weeks.

**M1-8 is next and is the one to protect** — it blocks G1, and it is the task where a
mistake invalidates every label written after it. Two things now waiting for it:

- **ADR-005's closing note on LaTeX.** `_DECORATION` in `runner/run.py` is the list of
  delimiters actually observed ending a response; C4.2 already requires the segmenter to
  treat `\[ … \]` as one sentence and never split inside a fence.
- **Arm 3's trace shape is ready for it.** `rlens.seq` carries the execution order because
  the serialised tree has no timestamps, and C3.2's `step_id` embeds an ordinal — ordering
  by span id would work until turn 10 sorted before turn 2. The ReAct path is structural
  only (one `tool_call` + one `observation` per TOOL span), so the segmenter has TOOL spans
  in `rlens.seq` order and the `reasoning` text on each LLM span to make thought steps from.

## W3 closed — 18.6 h against 7.5, and the segmenter is frozen

### The freeze went in with its precondition measured, not assumed

Breakdown §5.3 routes S3's two possible verdicts to two different places: too many steps
per call is a batch-size change in M1-9, steps too *long* is a **segmenter cap change that
must precede the tag**. So S3 ran first, and the number that mattered was not the parse
rate:

**The split cap fires on 0 of 261 thought steps.** Longest 130 words against a 138 cap,
median 21. Five traces have reasoning longer than the cap and C4.2's discourse-marker
splits had already broken every one of them below it before the cap was consulted. So *no
segmentation that exists today depends on `SPLIT_OVER_WORDS`*, and a later decision to
change it cannot retroactively renumber anything. That is the condition the freeze needed,
and it is a measurement rather than a hope.

### "25 is too many" was false, and the first measurement was measuring the wrong thing

S3's first pass looked conclusive: batch 10 clean 3/3, batch 25 failing 2/3, batch 50
failing 3/3. The obvious read is that C4.3's ~25-step assumption is wrong.

It is not. Three failure modes were hiding behind one symptom:

| | What it looked like | What it was |
| --- | --- | --- |
| `content` empty, 1,853–2,293 tokens billed | the model refusing | the whole output budget spent in the **reasoning** channel |
| `Unterminated string at char 3745` | malformed JSON | truncation, `finish_reason: length` at exactly 4,095 chars, three runs identical |
| 8 rows returned for 50 steps | a short answer | a silent give-up that C4.3's step_id rule catches |

All three are one cause: **an output cap of roughly 2,000 tokens, and
`max_tokens` is silently ignored on the OpenAI-compatible endpoint.** `max_tokens: 16000`
still returned `finish_reason: length` at 1,854 tokens, byte-identical across three runs.
Against the **native** endpoint with `options.num_predict`, batches of 10, **25 and 50**
all return a row per step with an exact `step_id` match.

> **This is the fifth parameter in this project accepted and ignored**, after
> `reasoning_effort: "none"`, native `think: false`, and the two in ADR-004. The rule the
> project keeps re-learning at its own expense: **verify a parameter from the OUTPUT, never
> from the fact that the request was accepted.** Here the cheap version is a
> `finish_reason` check, and M1-9 should treat `length` as a hard error rather than a parse
> failure worth retrying — retrying a truncated call just truncates again.

Analysis calls also want `think: low`. Classification is a labelling task, not a
deliberation task, and at the default effort a 25-step batch spent its entire budget
thinking and returned nothing. It is *also* faster: 17s against 48s at batch 10.

### Two defects the corpus found that the code review did not

Both came from running the segmenter over all 42 trees, which is worth noting as a method:
**the corpus is a better reviewer than reading is.**

1. **A trace with no visible answer was reported `full`.** `mb-08.thinking` produced 141
   reasoning steps and an empty `content`. Reasoning was present, so the quality rule —
   which only asked "did we get reasoning?" — called it full. There is no answer in that
   trace. Downstream it becomes `correct: false`, which asserts the model answered and was
   wrong, when it never answered. **This is M1-5's `unparsed`-vs-`wrong` distinction one
   layer up**, and the third time this project has had to separate "we could not read it"
   from "it was wrong".
2. **An unterminated code fence was unprotected.** A 70-word trace truncated mid-fence
   split into four steps, three of them lines of code. C4.2 says never split inside a
   fenced block — not "inside a fence that closes" — and S3 had just measured
   `finish_reason: length` on this runtime, so truncation is an observed shape. Fixed
   before the tag. Unterminated *maths* is deliberately left unprotected: a stray `\[` in
   prose would otherwise collapse everything after it into one unsplittable step, and
   over-protection has a cost too.

### What the 141-step trace actually shows, and why it is the best artifact of the month

126 of those 141 steps open with `Let's` and repeat the same sentence about a town that
does not exist. The segmenter is not over-splitting — each is a genuine marker-initial
sentence, and the model really did say one thing 126 times.

> **That is the product working.** *The thinking arm spent 3,966 reasoning tokens saying
> one thing 126 times, and never answered* is a claim nobody could make by reading a
> transcript, and it is exactly what B4 means by reasoning made measurable. It also argues
> for a near-duplicate-step signal in M1-9 or M2 — a "stuck loop" flag is one comparison
> away once steps are segmented, and it would be the cheapest genuinely novel metric in the
> plan.

### Capacity — the C10.1 bet, settled

**32.8 h spent against a 26.4 h month and a 12 h Lead allocation.** W3 alone ran **18.6
against 7.5**, 2.5x its budget, and it was already flagged in the plan as the heaviest week
with the least slack.

The like-for-like read still holds and is still the useful one. Of W3's 18.6 hours, the
**estimated work came in at 11.3** (M1-5's measurement 2.6/1.5, M1-7's loop 3.4/3.0, M1-8's
segmenter 2.4/2.0, S3 1.9/1.0, plus the ADRs those tasks require). The other **7.4 h is six
defects and three ADRs**, none of it rework and every one of it a thing that would have
surfaced later and cost more:

| Found in W3 | Would have surfaced as |
| --- | --- |
| `exact` scoring 37.5% of correct answers wrong | "the model is worse than expected", in M3 |
| the answer extractor returning `\]` | an unreadable answer counted as wrong |
| arms 1 and 2 never separating on accuracy | FE-1 built in W5 around a row that does not exist |
| a cwd-relative corpus path | arm 3 answering wrong on a *green* run with a plausible chain |
| a no-answer trace reported `full` | `correct: false` against a model that never answered |
| `max_tokens` silently ignored | M1-9 concluding its batch size must be 10 |

**The C10.1 bet is lost, and it is no longer a projection.** The month will land near **36 h
against 12 allocated** once M1-9, M1-10, M1-11, M1-13 and M1-14 are in. **G2 should draw the
Option-2 contingency**, and the W4 reading will be the fourth consecutive week saying so.

**Next is W4 and G1.** M1-9 (classifier) inherits three things from this week, all written
down rather than remembered: chunk with an explicit output cap and assert it took effect;
run analysis at `think: low`; treat `finish_reason: length` as a hard error. Then M1-10
freezes `ReasoningReport` at G1 — the one structural decision that makes 12 frontend hours
cover eight surfaces, and the deadline that E9 and E11 exist to protect.

---

## W5 — the 90 labels land, and the classifier turns out to be two instruments

**The block cleared.** M1-11 sat *blocked on a human* for four weeks — the only task in the
project that could not be bought with hours — and on 15 Sep it went, along with M2-1a's
held-out 50, in a single pass over the whole random-90.

### The result, and it is not one result

| | κ | n | baseline | B4 #2 (κ ≥ 0.60) |
| --- | --- | --- | --- | --- |
| **Soundness** | **0.761** | 40 | 0.625 | **met** |
| **Behavior** | **0.126** `[-0.138, 0.421]` | 40 | 0.850 | failed by a distance |

**The half nobody was worried about is the half that works.** Soundness clears B4 #2 and
clears the 0.70 that B4 #1 asks of *two humans*. It is the first criterion the classifier has
met on its own rather than through the judge.

**The behavior half agrees with a human less often than a constant would.** Raw agreement
0.70; answering `linear` to everything scores 0.85. **15 percentage points below the
majority-class baseline** is not a weak signal — it is a signal that costs accuracy to use.

That is ADR-010 arriving from the other side. The taxonomy barely populates, so the baseline
is brutal, and every non-linear call the classifier gets wrong costs more than a correct one
gains. **κ 0.126 is below G2-C's falsification threshold — and it is not a G2 reading**: G2
reads the *held-out* set at a *frozen* bundle, and this is the dev set against an **un-tuned
v0**. It is the number M2-3's box exists to move, recorded now precisely because a starting
point recorded afterwards is an estimate.

### The best thing in the week is a note written before the number existed

The labelling notes on `mb-08`'s repetition loop, blind, with no score in existence:

> *"A third of this loop opens with `Let's check:`, a likely verification cue for the
> classifier, so disagreement may cluster on this trace."*

**Four of the five false `verification` calls are in that loop.** `verification` precision is
0.286. The classifier is reading the marker, not the move — on a trace that emits the marker
126 times while recomputing nothing.

All 12 behavior disagreements fall into two buckets, and **both are open rubric questions
rather than prompt defects**: surface-marker cueing on loop prefixes, and goal-restatement
versus sub-goal on first steps. M2-3's card says to check exactly this before spending its
box — *"concentrated in one class … is a rubric-precedence problem rather than a prompt
problem and is fixed in the rubric."* It is concentrated. **So M2-2's rubric work comes before
M2-3's prompt work**, which is the order the plan already had, now with evidence under it.

### The defect the measurement exposed, and it is the worst kind

**C5.4's held-out guard was keyed on a filename.** `make calibrate`'s default — the
invocation M2-3 runs *every cycle* — excluded `heldout-50.jsonl` by name and nothing else. The
labelling tool writes `<annotator>.jsonl`. So both halves of the draw sat in one file, and
every dev number from here on would have silently included the 50 steps whose entire value is
that nothing was ever tuned against them.

**It would have fired in W6 regardless of how the labelling had gone.** `annotator-2.md` sends
the second annotator to `labels/<annotator>.jsonl`, and he labels *nothing but* the held-out
50 — so `ankit.jsonl` would have leaked the whole set on its own, with every guard green.

This is the fourth guard in this project to be *watched failing* before being trusted: the
import-linter contract, `check_rubric_drift.sh`, the `--dry-run` that exists because a smoke
test once wrote a fake label into the corpus, and now two regression tests that were run
against the un-fixed code first. **A guard nobody has watched fire is a guard nobody knows
works**, and this one had been green for five days while being wrong.

### On the hours, and a first

**W5 is at 47.9 against a 9.0 plan.** The labelling itself came in at **1.66 min/step mean
against the plan's assumed 1.6** — so **C10.3's labelling line is the first estimate in this
project to survive contact with the thing it estimated**, and M2-1a's overrun trigger does not
fire.

**It nearly fired on an artefact.** Read naïvely, the label file spans 3.1 h of wall clock,
which would have said 2.08 min/step and tripped the trigger. But rows 31–90 were judged first
and entered in batches of ten, so `labeled_at` records the write and not the reading; the only
clean sample is the 30 individually-stamped rows. **The pattern and the annotator's
confirmation are written into `calibration/README.md`** rather than left for an auditor to
find and misread — the same discipline the file asks of everything else.

**Cumulative: 96.2 h against a 12 h Lead allocation.** The C10.1 bet was lost in W3 and every
week since has said so louder.

### Next

**Two human-dependent rows, and they are the last of them** — see
[`month-3-unblock.md`](month-3-unblock.md):

1. **M2-2 — Ankit's independent pass**, ~2 h in W6. No substitute, no default; B4 #1 is not
   computable without it, and it gates classifier scoring. The agenda for the adjudication
   that follows is already written: [`adjudication-queue.md`](../calibration/adjudication-queue.md),
   14 questions with the reading actually applied and the labels a reversal would invalidate.
2. **M2-1b — the enriched 31**, ~50 min, needs nobody. Sequenced *after* M2-2 by its own card,
   so the adjudicated hard cases are in the rubric before the largest labelling block.

Then M2-3's box, against a rubric that has been argued rather than assumed.
