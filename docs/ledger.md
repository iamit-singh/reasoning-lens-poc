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

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 6.7 | **+3.4** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of amendment work, **1.4 h of W2 work pulled forward** (M1-15 + M1-16) and **0.5 h unbudgeted** (the tokenizer for G0 check 2). See the like-for-like note below |
| W2 | 6.7 | **8.9** | **+2.2** | **Complete.** M1-15, M1-16, M1-2, M1-6, M1-4 all done. 1.4 h of it was delivered in W1 |
| W3 | 7.5 | **11.7 to date** | | M1-5 closed at **6.4 against 1.5**; M1-7 at **5.3 against 3.0**. M1-8 and S3 not started. Already 4.2 over the whole week's budget with two tasks left |
| W4 | 8.0 | | | |
| **Total** | **26.4** *(25.5 + M1-2 0.6 + M1-6 0.9 − M1-4 rounding)* | **25.9 to date** | | |
| *vs. C10.2 Realistic* | 22.0 | | | *+3.0 = the four §1.3 gaps, less L1/L2* |
| *vs. Lead capacity* | 12.0 | | | *the C10.1 bet, first reading at end W4* |

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
