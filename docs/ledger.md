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
| 2026-09-10 | W1 | §11 | 0.3 | Day-1 unblock: four Appendix D asks drafted. **None sent** — each needs a human. D#1 default taken and recorded (Option 2, L1+L2 applied now) |
| 2026-09-10 | W1 | M1-3 | 0.4 | S5 DNS: ADR-003 written, ticket text ready to file verbatim. **Not filed** — no ticket ID, no named owner yet |
| 2026-09-10 | W1 | M1-1 | 0.8 | S1 harness written + self-tested (alias refusal, no-key path). ADR-001 committed as *Proposed* with all 4 branches pre-decided. **Run blocked: no API key** |
| 2026-09-10 | W1 | M1-0 | 1.5 | CI green across all 9 every-PR jobs; import-linter contract proven by a deliberate violation (`23defe3`) then reverted (`7b1ae59`) |
| 2026-09-10 | W1 | M1-1 | 1.2 | **Plan amendment 001**: hybrid runtime (local generation + OpenAI analysis), local-only demo, solo delivery. ADR-001 + ADR-003 rewritten; pin redefined as a tuple; S1 re-scoped; S6 tool-calling spike added; config, Makefile and 22 unit tests updated |
| 2026-09-10 | W1 | M1-15 | 0.8 | **W2-0 pulled forward** — M1-1/G0 was blocked on it. ollama 0.33.3 served natively; `gpt-oss:20b` pulled; full pin tuple recorded in `.env` **and** ADR-001. **0.3 over estimate**: two defects in `pin_local.sh` — it recorded ollama's truncated manifest id as the digest, and emitted `LOCAL_RUNTIME` unquoted so sourcing `.env` silently truncated it |
| 2026-09-10 | W1 | M1-1 | 0.6 | **S1 local arm: PASS.** 2535 chars of raw reasoning in a `reasoning` field, not inline `<think>` tags. ADR-001's G0 table filled from the real run. **G0 check 2 closed off as NOT met** |
| 2026-09-10 | W1 | M1-16 | 0.6 | **S6: PASS, 20/20** — 100% on all four scenarios incl. tool-choice and the false-positive check. Arm 3 is buildable; the `qwen3:14b` fallback is not needed |

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 6.2 | **+2.9** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of amendment work **and 1.4 h of W2 work pulled forward** (M1-15 + M1-16). See the like-for-like note below |
| W2 | 6.7 | *(1.4 delivered in W1)* | | M1-15 and M1-16 are **done** — 1.0 h planned, 1.4 h actual. 5.7 h of W2 remains |
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
> **Like-for-like, W1's own tasks came in at 3.6 h against 3.3 h planned — +0.3.** That is
> the honest reading of W1 execution, and it is close to estimate.
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