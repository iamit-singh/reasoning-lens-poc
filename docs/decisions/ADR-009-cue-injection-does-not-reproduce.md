# ADR-009 — Cue injection does not reproduce on this model

| | |
| --- | --- |
| **Status** | **Proposed** — 11 Sep 2026 (W4) |
| **Decided by** | Amit Singh (sole contributor) |
| **Evidence** | [S4 — cue injection](../spikes/S4-cues.md) · 48 trials, 4 cue types, 2 regimes |
| **Affects** | §C4.7 faithfulness study · **M2-9** (3.5 h) · **FE-5** · **B4 #6** · **B6.3** the demo's wow moment |
| **Precedent** | [ADR-005](ADR-005-traps-do-not-reproduce.md) (traps), [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md) (arm separation) |

## Context

C4.7 builds a faithfulness study on Turpin et al. ([arXiv:2305.04388](https://arxiv.org/abs/2305.04388)):
plant a cue pointing at a wrong answer, see whether the model takes it, and see whether the
reasoning trace admits to having taken it. A model that flips *and* stays silent about the
cue is reasoning unfaithfully, and B6.3 makes that panel the demo's most striking moment.

M2-9 budgets 3.5 hours and over-provisions deliberately: **12 candidate cue/problem pairs
to find 3.** S4 exists to test, four weeks early, whether that over-provisioning is enough.

## The measurement

**0 of 48 trials flipped.** Four cue types — every one Appendix A.4 names — across two
problem regimes, six problems, three repeats each.

| Cue type | Trials | Flipped |
| --- | --- | --- |
| Metadata leak `<!-- key: X -->` | 12 | **0** |
| Authority | 12 | **0** |
| Sycophancy | 12 | **0** |
| Few-shot pattern | 12 | **0** |

Three things make this a finding rather than a broken harness:

1. **The cue reaches the model and the model notices it.** On the `unverifiable` problem it
   verbalised the cue on every trial of every type — naming the hint, discussing it, and
   answering what it was going to answer anyway.
2. **The problems were varied to remove the obvious confound.** A first pass used only
   problems the model can solve, which measures the problems as much as the cues: refusing
   a hint you can check is not evidence of faithfulness. A second regime asked about
   entities that exist only in this project's fact corpus, where arm 2 has no tools and
   nothing to weigh the cue against. Still zero.
3. **The strongest cue was included.** The few-shot pattern never states an answer; it
   establishes one across three correct worked examples. It is the cue most likely to be
   acted on without being verbalised, because there is nothing explicit to verbalise.

**A second observation, possibly the larger one.** Two of the three `unverifiable` problems
returned **completely empty content** — zero characters, reasoning tokens billed. Asked
something it cannot look up, this model does not guess; it loops. That is the same shape as
`mb-08.thinking`, which spent 3,966 reasoning tokens saying one sentence 126 times about a
town that does not exist and never answered.

## Decision

**Withdraw the assumption that a cue type can be found by search, and take option 1: the
negative result is the finding, published as one.**

| # | Option | Cost | Verdict |
| - | --- | --- | --- |
| **1** | **Publish the negative result.** *"Four cue types, 48 trials, zero flips"* becomes the faithfulness section | ~0.5 h; M2-9 drops from 3.5 h to ~1.0 h | ✅ **Recommended** |
| 2 | Redesign the cue as something the model is *instructed to trust* — a retrieved document, a tool result | Unknown, and materially different work from what M2-9 budgets | ⏸️ Hold — see below |
| 3 | Change the subject model until a cue works | — | ❌ **Forbidden.** ADR-001's same-model rule exists so the arms compare strategies rather than vendors. Selecting a model *because* it is unfaithful would also be selecting the result |
| 4 | Drop the study, re-scope FE-5 | Recovers 3.5 h in the tightest month; loses the demo's best panel | ⏸️ Fallback if option 1's panel reads as thin |

### Why option 1 rather than option 2

B0 Condition #5 already commits this project to publishing whatever the numbers turn out to
be, and it is a commitment that has now been tested three times in one month. *"We planted
four kinds of misleading cue 48 times and this model took none of them"* is a real claim
about a real model, it is cheap, and it is honest.

Option 2 is a genuinely interesting bet and it is **held rather than rejected**: a cue
embedded in a retrieved document is a different mechanism from a remark the model can
dismiss, and it is closer to how unfaithfulness would actually show up in a product. But
it is new experiment design, it lands in Month 2's tightest week, and S4's own numbers say
nothing about whether it would work. **Taking it on the strength of a hunch, in the month
with no slack, is how M2-9 becomes a 7-hour task.** If option 1's panel reads as thin at
G2, option 2 is the first thing to buy with the contingency.

### What the panel says instead

The faithfulness panel keeps its slot and changes its claim. Rather than *"the model was
misled and hid it"*, it shows the experiment and its result: the cue, the trace that names
the cue, the answer that did not move, and the count. **A panel that shows a null result
honestly is still a panel about faithfulness** — and it is a considerably harder thing for
a reviewer to dismiss than a single cherry-picked flip would have been.

## Consequences

1. **M2-9 is re-scoped from 3.5 h to ~1.0 h** — run the existing harness at larger n on the
   full bank, write the panel. **This is the first task in Month 1 to give hours back**,
   and it lands in the month that needs them most.
2. **FE-5 changes what it renders**, not how much. Side-by-side hinted/unhinted, the cue
   highlighted, and the callout inverted: *"the trace names the hint and answers the same
   thing anyway"*. The `faithfulness/panel.json` shape in C3.4 already carries `flipped`
   and `hint_verbalised`, so no schema change.
3. **B4 #6's claim is re-worded.** It cannot be "hint-verbalisation rate" when nothing is
   hinted into. It becomes a measured **cue-resistance** rate, with n and the cue types
   named.
4. **The `unverifiable` empty-content behaviour needs a decision of its own.** A model that
   loops instead of answering is a real property this instrument can measure, and it is
   currently landing as `trace_quality: partial` with `correct: null`. It may deserve a
   named metric — M1-8's write-up already argued for a near-duplicate-step signal on the
   same evidence, and this is the second time that signal would have been the interesting
   number.
5. **S4 stays in the repo and stays runnable.** If the pin changes, `make spike-s4` is one
   command and the claim is re-measurable. A negative result that cannot be re-run is an
   assertion.

## The pattern this is the fourth instance of

Month 1 has now measured four phenomena the plan assumed would be there, and found all four
smaller than expected or absent: traps that do not reproduce, arms that do not separate on
accuracy, a behavior taxonomy that barely populates, and cues that do not move the answer.

**That is not four failures. It is one finding, arrived at four times: the instrument works,
and the effects it was pointed at are smaller than the plan expected.** It belongs in the
G2 measurement report as a stated result rather than as four separate apologies — and it is
worth noticing that every one of them was cheap precisely because the plan ordered the
measurement before the thing that depended on it.
