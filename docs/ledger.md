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

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 6.7 | **+3.4** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of amendment work, **1.4 h of W2 work pulled forward** (M1-15 + M1-16) and **0.5 h unbudgeted** (the tokenizer for G0 check 2). See the like-for-like note below |
| W2 | 6.7 | **8.9** | **+2.2** | **Complete.** M1-15, M1-16, M1-2, M1-6, M1-4 all done. 1.4 h of it was delivered in W1 |
| W3 | 7.5 | **18.6** | **+11.1** | **COMPLETE.** M1-5 6.4/1.5 · M1-7 5.3/3.0 · M1-8 5.0/2.0 · S3 1.9/1.0. `segmenter-frozen-v1` tagged. The heaviest week on the plan ran 2.5x its budget |
| W4 | 8.0 | **15.5 to date** | | M1-9 4.5/3.0 · M1-10 4.9/1.5 · M1-11 2.6/2.0 (tooling; labels are not the Lead's to fabricate) · M1-13 2.1/1.0 · M1-14 0.7/0.5 · M1-1 0.7. **M1-13 is the first task to give hours back** — ADR-009 re-scopes M2-9 from 3.5 h to ~1.0 h |
| **Total** | **26.4** *(25.5 + M1-2 0.6 + M1-6 0.9 − M1-4 rounding)* | **48.3** | **+21.9** | **Month 1 closed at 48.3 h against 26.4 planned and 12.0 allocated.** Two tasks are not finished — see the Month-2 table |
| *vs. C10.2 Realistic* | 22.0 | | | *+3.0 = the four §1.3 gaps, less L1/L2* |
| *vs. Lead capacity* | 12.0 | | | *the C10.1 bet, first reading at end W4* |

## Month-2 planned-vs-actual

Month 2 is W5–W8. **W5 started before Month 1 finished**, which is a statement about
sequencing rather than about discipline: M1-9's DoD measurement is compute, not keystrokes,
and M1-11's 40 labels are not the Lead's to fabricate. Both are named below rather than
quietly carried.

| Week | Planned (breakdown) | Actual | Δ | Notes |
| ---- | ---- | ---- | ---- | ------ |
| W5 | 9.0 | **19.0 to date** | **+10.0** | M2-13 2.3/1.5 · FE-1 3.2/1.5 · FE-2a 1.4/2.0 · FE-3+FE-4 1.8/3.5 · FE-6 1.2/1.0 · FE-7 0.4/0.5 · M2-5 2.1/2.0 *(part)* · M2-8 1.6/3.0 *(part)* · M2-4 prep 0.7 · plus 2.9 h of Month-1 spill (ADR-010, the harness fixes, the labelling guard) and 1.4 h of Month-3 backend pulled forward |
| **Month 2 total** | **~34** | **19.0 to date** | | |

> **Six of the eight frontend surfaces came in 1.9 h *under* their combined estimate**, and
> that is the first sustained underrun in this project. The reason is worth writing down
> because it was bought deliberately: they render a **frozen** object against **committed
> fixtures**, so every one of them was built without a running backend, without a model, and
> without a single question that needed an answer from somewhere else. That is precisely
> what G1 was for. The gate cost W4 dearly and W5 is where it pays back.

### Two Month-1 tasks are still open, and neither is idle time

| Task | State | What it needs |
| --- | --- | --- |
| **M1-9** | DoD unmet | The 20-run measurement. Best evidence so far is **1 degraded arm in 630 calls (0.16%)** against a 2% bar — but 13 runs is not 20, and the shortfall is an interrupted machine, not a failing classifier. ~100 min of compute |
| **M1-11** | **Blocked on a human** | 40 labels, in seeded order, both labels in one pass. The tool is built, blind, and dry-runnable. **This is the single highest-value 1.5 h left**: ADR-010's zero for `backtracking` cannot be settled by any amount of further code |

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
