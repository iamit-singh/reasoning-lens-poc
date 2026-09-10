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

## Month-1 planned-vs-actual

| Week | Planned (breakdown) | Actual | Δ | Notes |
| -------- | ---- | ---- | ---- | --------- |
| W1 | 3.3 | 4.2 | **+0.9** | Planned drops 0.5 (DNS cancelled). Actual carries 1.2 h of unplanned amendment work — the cost of three constraints surfacing on day 2 |
| W2 | 6.7 | | | +1.0: local-runtime setup and the S6 tool-calling spike, both added by the amendment |
| W3 | 7.5 | | | |
| W4 | 8.0 | | | |
| **Total** | **25.5** *(was 25.0: −0.5 DNS, +1.0 new spikes)* | | | |
| *vs. C10.2 Realistic* | 22.0 | | | *+3.0 = the four §1.3 gaps, less L1/L2* |
| *vs. Lead capacity* | 12.0 | | | *the C10.1 bet, first reading at end W4* |

> **⚠️ W1 came in over, and the reason is worth reading.** M1-0 landed on estimate. The
> overrun is 1.2 h of plan amendment — work that existed only because three constraints
> (no Anthropic access, no deployment, one person) surfaced on day 2 rather than at kickoff.
> That is cheap at 1.2 h and would not have been cheap in Month 3, which is the argument for
> front-loading risk in the first place.
>
> **The unflattering half:** the amendment releases ~4.9 h from Month 3 but *adds* 1.0 h to
> Week 2, which was already the second-heaviest week. The relief arrives ten weeks after the
> cost. The first reading that means anything is still **end of W4**.
