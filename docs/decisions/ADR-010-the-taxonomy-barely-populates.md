# ADR-010 — The behavior taxonomy barely populates, and κ inherits the problem

| | |
| --- | --- |
| **Status** | **Proposed** — 11 Sep 2026 (W4) |
| **Decided by** | Amit Singh (sole contributor) |
| **Evidence** | M1-9's full bank × 3 arms pass (310 rows) · `make taxonomy-coverage` (261 thought steps, no model) |
| **Affects** | **B4 #1** (κ ≥ 0.60, per-class F1 ≥ 0.50) · C5.1 two-part frame · C5.5 · **M2-1, M2-3, M2-14** · G1 check 3 |
| **Precedent** | [ADR-005](ADR-005-traps-do-not-reproduce.md), [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md), [ADR-009](ADR-009-cue-injection-does-not-reproduce.md) |

## Context

C4.3 adopts Gandhi et al.'s five-class taxonomy, and B4 #1 promises two numbers over it:
Cohen's κ ≥ 0.60 between two annotators, and per-class F1 ≥ 0.50. Both assume the classes
occur.

## The observation

Over a full pass of the bank × 3 arms, the classifier produced:

| `linear` | `verification` | `subgoal_setting` | `backward_chaining` | `backtracking` |
| --- | --- | --- | --- | --- |
| 252 (81%) | 35 (11%) | 22 (7%) | 1 (0.3%) | **0** |

**81% of steps are one class, and two of five classes have ≤ 1 instance in the entire
corpus.**

## The confound, checked before concluding anything

A zero has two readings with opposite consequences:

* *"This model does not backtrack"* — a claim about the **corpus**. Fix: harder problems.
* *"The classifier does not detect backtracking"* — a claim about the **classifier**. Fix:
  M2-3's prompt iteration, which is already budgeted for exactly this.

**Nothing in the classifier's own output distinguishes them**, so `make taxonomy-coverage`
measures the corpus with no model at all: how many steps *open* with a surface marker the
segmenter already treats as a discourse signal.

| Class | Steps opening with a surface marker | Traces containing any |
| --- | --- | --- |
| `backtracking` | **11 of 261 (4.2%)** | **2 of 42** |
| `verification` | 0 | 0 |
| `subgoal_setting` | 0 | 0 |
| `backward_chaining` | 0 | 0 |

And the eleven look like this:

> *"Actually there is a Fairhaven in New Zealand? I think there is a Fairhaven in New
> Zealand?"*
> *"Wait, there is a Fairhaven in New Zealand? I recall a Fairhaven in New Zealand? Not
> sure."*

All eleven are inside `mb-08.thinking` and `mb-09.thinking` — the traces that loop. They
open with a backtracking marker and **reverse nothing**, which `rubric.md` hard case 4.2
adjudicates as `linear` in advance and on purpose.

**So the classifier's zero is plausible rather than proven wrong**, and the corpus's
*opportunity* for backtracking is itself close to nil and concentrated in a degenerate
trace. The two readings have not been separated; they have been narrowed to one that says
*the corpus offers almost nothing to detect.*

> **Only a human reading those steps settles it.** That is M1-11's 40 labels, and it makes
> them the most valuable 1.5 hours left in Month 1 rather than a box to tick.

## Decision

**Do not change the bank, do not tune the classifier, and change what is reported.**

### 1. A class with no instances reports "not computable", never 0.0

Per-class F1 over zero instances is undefined. Reporting it as `0.00` says *"the classifier
is perfectly bad at this class"*, which is a measurement claim made from no measurements —
and it is the exact failure I3 exists to prevent. `measurement_context.per_class_f1` is
already `{"type": ["number","null"]}` per class, so **null is available and is what M2-1
must write**, with `n` beside it.

### 2. The majority-class baseline is not a footnote

C5.5 already requires it. With `linear` at 81%, an annotator who labelled everything
`linear` would score 81% raw agreement. **κ corrects for that, and corrects hard**: under
skewed marginals, high agreement routinely produces low κ — the κ paradox. B4 #1's target
of 0.60 was set without knowing the marginal was this skewed.

**This is a live threat to the headline number, raised at G1 rather than discovered at G2.**
It is not a reason to move the target; it is a reason to publish the baseline beside it and
to say plainly what a κ of, say, 0.45 would mean on a corpus where four fifths of the steps
are one class.

### 3. The enriched-60 must not be defined by the classifier alone

This is the load-bearing decision, and it is the one that would have been easy to get wrong.

C5.1's enriched-60 over-samples classes the classifier says are rare, so per-class F1 has
instances to be computed over. But **if the enrichment is defined purely by classifier
predictions, and the classifier never predicts `backtracking`, the enriched draw can never
contain a `backtracking` step.** The blind spot selects the sample that is supposed to
detect the blind spot.

So M2-14's enriched draw takes **two strata**:

| Stratum | Selected by | Guards against |
| --- | --- | --- |
| predicted-rare | the classifier's own low-frequency predictions | the corpus being unbalanced |
| **marker-bearing** | `make taxonomy-coverage`'s surface markers — **no model involved** | **the classifier's blind spot being invisible to itself** |

The second stratum is cheap: the script exists, it needs no model, and it already names the
eleven candidate steps.

### 4. G1 check 3 is met by an authored fixture, and the repo says so

No harvested report can carry five classes because no trace contains five classes.
`report_nominal.json` is authored and labelled as authored; `report_measured.json` is real
and labelled as real; tests assert neither can be mistaken for the other. See the
[fixtures README](../../analyzer/tests/fixtures/reports/README.md).

### What was rejected

| Option | Why not |
| --- | --- |
| **Add harder bank items** so the behaviours appear | A bank change after the segmenter freeze re-segments and re-draws everything (Hazard 1 and 2 together), in the month with no slack. And ADR-006 already measured that harder items do not separate the arms — there is little reason to expect they would populate the taxonomy either |
| **Tune the classifier now** to find more `backtracking` | That is M2-3, it is time-boxed, dev-set only and changelogged, and doing it in W4 against eyeballed output is exactly what M1-9's scope forbids. Worse: tuning a classifier to produce more of a class, before any human label exists to check it against, is fitting the instrument to the expectation |
| **Drop the two empty classes** from the taxonomy | The taxonomy is from the literature (Gandhi et al. §A3) and comparability to it is part of the claim. A class that does not occur is a finding about the corpus; deleting it hides the finding |

## Consequences

1. **M2-1 reports per-class F1 with `n`, and null where `n = 0`.**
2. **M2-14's enriched draw gains a model-free stratum.** Small change, and it is the
   difference between a sample that can detect the classifier's blind spot and one that
   inherits it.
3. **B4 #1's κ target is carried unchanged into G2 with the baseline beside it.** If κ comes
   in below 0.60 on an 81%-`linear` corpus, that is a result to interpret, not a failure to
   explain away — and the interpretation is already written down here, before the number
   exists.
4. **`make taxonomy-coverage` is committed and re-runnable.** If the pin or the bank
   changes, the claim is re-measurable in one command.

> **The fourth instance of one pattern.** Traps that do not reproduce, arms that do not
> separate, cues that do not move an answer, and now a taxonomy that barely populates.
> Every one was found by measuring before building on it, and every one was cheap for that
> reason. The instrument works. The effects it was pointed at are smaller than the plan
> expected — and *that*, stated with its numbers, is a more interesting result than the one
> the plan hoped for.

---

## Amendment, 12 Sep 2026 (W5) — **the zero was one run, and one run is not stable**

This ADR's headline was *"`backward_chaining` has 1 instance in the whole corpus and
`backtracking` has 0."* That was measured over **a single full-corpus pass**. M1-9's
reliability measurement has since run the same corpus **twelve times** —
`docs/spikes/M1-9-raw/m1-9-reliability.full.json`, 504 trace-runs, **3,579 rows**.

| Class | This ADR (1 run) | 12 runs | Share |
| --- | --- | --- | --- |
| `linear` | 252 | 2,944 | **82.3%** |
| `verification` | 35 | 288 | 8.0% |
| `subgoal_setting` | 22 | 269 | 7.5% |
| **`backtracking`** | **0** | **71** | **2.0%** |
| `backward_chaining` | 1 | 7 | 0.2% |

**`backtracking` is rare, not absent.** Per run it fires between **1 and 15 times**
(`[14, 3, 4, 15, 1, 3, 3, 13, 11, 2, 1, 1]`), and a run returning 0 sits comfortably inside
that spread. This ADR read a corpus-level property off n=1 run of a **non-deterministic
classifier**. The error was not the arithmetic; it was the inference.

> **This is the same mistake this project has caught twice before, committed by this
> project.** ADR-005 held its trap threshold rather than lowering it after a small sample.
> ADR-006 refused the difficulty contrast on the strength of one ad-hoc probe and measured
> it across the corpus instead. ADR-010 then did exactly what both of those refused to do.
> **The correction cost nothing only because M1-9's DoD happened to re-run the same corpus
> twelve times for an unrelated reason.**

### What still stands, and it is most of it

- **The distribution is still overwhelmingly `linear` at 82.3%**, which is the finding that
  matters for κ: the majority-class baseline is high, and κ will read low against it however
  good the classifier is. B4 #2's 0.60 target was set without knowing the marginal was this
  skewed, and that remains raised.
- **`backward_chaining` at 0.2% is still effectively absent** — 7 rows in 3,579, most runs
  producing none. Per-class F1 for it will be unstable or undefined, and B4 #2's "lowest
  per-class F1 ≥ 0.50" is at risk on that class alone.
- **The corpus-side confound check is unaffected.** It used no model, and 11 of 261 thought
  steps (4.2%) opening with a backtracking marker is still the ceiling on how often the
  behaviour could genuinely occur. **2.0% measured against a 4.2% ceiling is *consistent*,
  which is a stronger position than 0% against 4.2% was.**
- **M1-11's 40 labels are still the most valuable hours left**, for the reason this ADR
  gave: nothing in the classifier's own output says whether its 2.0% is the *right* 2.0%.

### Where the rare class fires, which is informative for the labeller

45 of the 71 `backtracking` rows are in `mb-08.thinking` — **the trace that loops 126 times
over a town that does not exist**. A model repeating itself and occasionally saying
*"actually…"* is the one place in this corpus where the behaviour has something to attach
to. The other site is `mb-10.direct` at **25% of its rows**: a short trace and a small
denominator, but worth a labeller's attention precisely because it is where the class looks
common.
