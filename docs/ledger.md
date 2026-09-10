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

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 6.7 | **+3.4** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of amendment work, **1.4 h of W2 work pulled forward** (M1-15 + M1-16) and **0.5 h unbudgeted** (the tokenizer for G0 check 2). See the like-for-like note below |
| W2 | 6.7 | 6.9 *(so far)* | | M1-15, M1-16, M1-2, **M1-6 done** — 5.5 h planned *(M1-6 revised to 3.0)*, 6.9 h actual, **+1.4**. **Only M1-4 (1.7 h) remains in W2** |
| W3 | 7.5 | | | |
| W4 | 8.0 | | | |
| **Total** | **25.5** *(was 25.0: −0.5 DNS, +1.0 new spikes)* | | | |
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
