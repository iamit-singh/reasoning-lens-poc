# G2 measurement report

**Reasoning Lens PoC · Month 2 · Gate G2 · written 16 Sep 2026 (W6)**

> **How to read this in one hour.** §1 names the branch and the two numbers that decide it.
> §2 is every B4 criterion with its n and interval. §10 is what makes §§2–9 believable.
> §12 is the hours, and it is half the decision you are being asked to make.
>
> **Nothing in this document asks you to design anything.** C1.3 pre-decided all three
> branches; G2 is a choice between them.

---

## 1. The branch

> # G2-B — and it is **one label of fifty** away from G2-C
>
> **Pooled judge precision 0.643 [0.388, 0.837], n = 14** — below the 0.75 bar.
> **Held-out classifier κ: 0.550 [−0.017, 1.000] against annotator 1 · 0.401 [−0.017,
> 0.792] against annotator 2**, n = 50, majority baseline 0.920.

C1.3's rule: `κ_heldout < 0.60 OR precision < 0.75` → **G2-B**; `κ_heldout < 0.45 OR
precision < 0.60` → **G2-C**. Precision (0.643) is a G2-B input either way. **The κ is not:
0.550 is G2-B and 0.401 is G2-C**, and which one you get depends on whose labels are
treated as ground truth.

### The two annotators disagree on exactly one behavior label in the held-out 50, and that label moves the gate

| | | |
| --- | --- | --- |
| Step | `direct:direct-mb-06-root-llm-0:1` | |
| **Annotator 1 (amit)** | `verification` | wrote `rubric.md` **and** the classifier prompt |
| **Annotator 2 (ankit)** | `backtracking` | labelled blind, from the written rubric alone |
| **The classifier** | **`verification`** | agrees with the rubric's author |

They agree on the other 49. That single step is worth **0.149 of κ** — because with 46 of
50 steps `linear`, four non-linear steps carry the entire coefficient, so one of them is a
quarter of the signal.

> **The direction matters and is stated rather than left for the reviewer to notice.** The
> higher κ comes from scoring against **the person who wrote the rubric the classifier was
> given**. The independent reading — the blind second pass, which is the whole point of
> having one — gives the lower number and the worse branch. **There is no adjudication to
> settle it**: M2-2's adjudication is *by discussion* and amendment 002 dropped it, so this
> step has two readings and no resolution, and choosing one after the predictions are known
> is exactly what finding 14 was written to prevent.
>
> **This report therefore does not pick.** It names G2-B because precision independently
> requires at least G2-B and because the primary scoring set is the annotator who labelled
> the whole draw — and it records that a defensible reading of the same 50 steps yields
> G2-C. **That choice is the reviewer's, and it is the one decision at this gate that the
> evidence genuinely does not make for them.**

**What G2-B costs: ~0.5 h of Month-3 UI delta.** Same demo, same architecture. Soundness
renders with a prominent measured-error-rate chip, the verdict line hedges, and the
calibration page leads with the shortfall. **No rescope, and nothing to improvise.**

**The reviewer's decision is recorded here:** `_______________` (G2-A / G2-B / G2-C)

---

## 2. Every B4 criterion, with n and interval

| # | Criterion | Target | Measured | n | Interval | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Inter-annotator κ | ≥ 0.70 | **behavior 0.867** · soundness 0.935 | 50 | [0.495, 1.000] · [0.766, 1.000] | **MET** ¹ |
| 2 | Classifier κ (held-out) | ≥ 0.60 | **0.550** (ann. 1) · **0.401** (ann. 2) | 50 | [−0.017, 1.000] · [−0.017, 0.792] | **NOT MET** on either reading |
| 2 | Soundness κ (held-out) | — | **0.822** (ann. 1) · **0.885** (ann. 2) | 50 | [0.603, 1.000] · [0.696, 1.000] | **clears 0.60 on both** |
| 2 | Per-class F1, lowest — **dev** | ≥ 0.50 | **0.000** | 1–4 per class | — | **NOT MET** ² |
| 2 | Per-class F1, lowest — **held-out** | ≥ 0.50 | **0.500** (`verification`) | **3** | — | **MET, at n = 3** ² |
| 3 | Judge recall (seeded) | ≥ 70% | **8 / 10 = 0.80** | 10 | triage-alone, shipped config | **MET** ³ |
| 4 | Judge precision (pooled) | ≥ 0.75 | **0.643** | 14 | [0.388, 0.837] | **NOT MET** |
| 4 | False flags / known-good trace | ≤ 1.0 | **NOT MEASURABLE** | — | — | **SHORTFALL** ⁴ |
| 5 | Consistency FP | ≤ 5% | **0 of 5 traces** | 5 | — | **MET, read as zero** ⁵ |
| 6 | Faithfulness reproduces | ≥ 2 of 3 | **0 of 48 trials flipped** | 48 | — | **NOT MET — published as a finding** ⁶ |
| 7 | Cost of thought visible | reported | **median 5.13×**, range 1.22–53.59× | 14 | — | **REPORTED** ⁷ |
| 8 | p90 latency | < 5 s cached | **1.0 ms** | 140 | p50 0.9 / p99 1.3 ms | **MET (cached half)** ⁸ |
| 9 | 5 testers, ≥ 4 state the insight | 4 of 5 | **UNMEASURED** | 0 | — | **LOST** ⁹ |
| 10 | Uptime / spend | — | uptime n/a; spend from the breaker file | — | — | **REPORTED** ¹⁰ |

¹ Unadjudicated and the annotator's confirmation is **unsigned** — see §10. Adjudication
normally *raises* agreement, so this ships as a **floor**. 2 of 50 steps contested, both
published with both readings. The CI runs to 0.495, below the bar it clears: 46 of the 50
steps are one class and four non-linear steps carry the whole coefficient.

² §2.2 requires this published **twice**, and the two disagree. **Dev: 0.000** — three of
five classes have n ≤ 1 and one has n = 0. **Held-out: 0.500**, which clears the bar
**on a support of 3**, with two classes absent entirely (`backtracking` n = 0,
`backward_chaining` n = 0). **Neither figure is a statement about the classifier**, and the
held-out one clearing the bar is the more misleading of the two: it is one class, three
steps, and a bar that a single label would move either side of. See §4.

³ **Escalation is shipped off** and this is the triage-alone number. With escalation on it
is 7/10 — see §6 and finding 16.

⁴ B4 #4's second clause needs every step of five traces human-labelled (M2-15), which
amendment 002 dropped. **A per-labelled-step rate is published instead: 0.000
[0.000, 0.242], n = 12 labelled steps, 0 false flags.** The conversion to per-trace is
stated rather than performed — §1.3.1's fallback, taken knowingly.

⁵ At n = 5 the smallest non-zero rate is 20%, so a 5% bar and a 0% bar are the same bar on
this denominator. Published as a **count**.

⁶ ADR-009. **0 of 48 trials flipped, across all four Appendix A.4 cue types and both
problem regimes.** The negative result is the artifact: it has a denominator and it is
falsifiable by re-running `make spike-s4` at a different pin. 3 trials returned **no answer
at all** — reasoning tokens billed, zero characters out.

⁷ Appendix D #8 was never answered; **the default was taken** — reporting criterion, not a
gate. §9.

⁸ Server-side, over loopback, on a path C4.9 forbids from triggering a model call. **It is
evidence the rule holds, not that the service is fast under load** — nobody has put it
under load. The live half is deleted scope (ADR-003) and is labelled not-applicable rather
than left empty.

⁹ **The only criterion testing whether the demo *communicates*.** No testers exist;
amendment 002 §2 declines to substitute the agent for a naive viewer. Published as a
shortfall on the calibration page rather than lowered until it passes.

¹⁰ Nothing is deployed (ADR-003), so there is no uptime to report. Spend reconciles from
the breaker's own file (ADR-011), which `make trip-breaker` exercises.

---

## 3. κ, four ways — and the reason this section is a range, not four numbers

| | κ | n | baseline | note |
| --- | --- | --- | --- | --- |
| **IAA, human vs human** | **0.867** behavior · 0.935 soundness | 50 | — | B4 #1. Unadjudicated floor |
| **Classifier, held-out** | **0.550** / **0.401** | 50 | **0.920** | The published headline — two readings, see §1 |
| **Classifier, dev** | **−0.052 … +0.186** over five runs | 32–40 | **0.850** | See below |
| **Majority-class baseline** | **0.850** | 40 | — | Always answering `linear` |

### The dev κ is published as a range because a point would be fiction

Five runs at the **same frozen bundle**, nothing changed between them:

| n | agreement | `linear` predicted | κ |
| --- | --- | --- | --- |
| 40 | 0.775 | 35 | **+0.104** |
| 32 | 0.8125 | 31 | −0.032 |
| 32 | 0.8125 | 29 | **+0.186** |
| 32 | 0.781 | 30 | −0.052 |
| 40 | 0.825 | **39** | −0.026 |

**Range 0.238. SD 0.132.** Two of those runs have **identical n and identical 26-of-32
correct with κ 0.218 apart**, purely because one spread its errors across three classes and
the other put them all in `linear`.

**The mechanism is arithmetic, not mystery.** κ = (p_o − p_e)/(1 − p_e), and on a set that
is 85% one class, p_e moves faster than p_o can follow. A classifier that predicts `linear`
30 times has a *lower* p_e than one predicting it 34 times — so being wrong in a
differently-shaped way **flatters κ**. During M2-3, fixing five genuine false positives
moved p_e from 0.657 to 0.728 and took κ *down* with it while the classifier got two more
steps right.

> **What this does to B4 #2's 0.60 bar, stated as arithmetic rather than as an excuse.** At
> p_e ≈ 0.73, κ ≥ 0.60 requires **35.6 of 40 steps correct — at most 4 errors**. The bar was
> set without reference to this corpus's class balance, and on an 85%-majority sample it
> asks for near-perfect agreement rather than for a good classifier. **The bar is not being
> moved** — C7.2's recorded-justification branch was available and was **declined**, because
> a gate whose metric has a 0.238 run-to-run range does not improve by being lowered. It is
> reported against, with the arithmetic shown. Finding 15.

### The dev–held-out gap — and it points the wrong way

C5.7 asks for the dev-minus-held-out gap as an overfitting reading. **It is negative here:
dev κ ranges −0.052 to +0.186 and the held-out κ is 0.401–0.550. The held-out set scores
*better* than the set the prompt was tuned on.**

That is not evidence of good generalisation. It is the baseline moving: the held-out draw is
**92% `linear`** against the dev set's 85%, and 46 of its 50 steps are one class. Raw
agreement on the held-out 50 is **0.940 against a 0.920 baseline — 2.0 percentage points
above always answering `linear`**, on four non-linear steps.

**Read the held-out κ against the 0.920 baseline of its own draw, never against the dev
figure.** The gap between them measures the two draws' class balance, not the classifier.

---

## 4. Per-class F1, and why only one row is a measurement

**Held-out (50 steps, read once — the published set):**

| class | F1 | support | predicted |
| --- | --- | --- | --- |
| `linear` | 0.968 | 46 | 47 |
| `subgoal_setting` | 0.667 | 1 | 2 |
| `verification` | **0.500** | **3** | 1 |
| `backtracking` | **n/a** | **0** | 0 |
| `backward_chaining` | **n/a** | **0** | 0 |

**Two of five classes do not appear in the held-out draw at all**, and a third has a support
of 1. B4 #2's *"lowest per-class F1 ≥ 0.50"* is **met on this table at 0.500** — one class,
three steps. One label either way moves it across the bar. It is reported, and it is not
evidence of anything.

**Dev (40 steps, tuned-on):**

| class | F1 | support | predicted |
| --- | --- | --- | --- |
| `linear` | 0.904 | 34 | 39 |
| `verification` | 0.000 | 4 | 0 |
| `subgoal_setting` | 0.000 | 1 | 1 |
| `backtracking` | 0.000 | 1 | 0 |
| `backward_chaining` | **n/a** | **0** | 0 |

**Only the `linear` row has a support large enough to mean anything.** B4 #2's *"lowest
per-class F1 ≥ 0.50"* is **not met**, and it is not met on cells with n = 1, n = 1 and
n = 0 — which is a fact about the sample, not a measurement of the classifier. Reporting
`backtracking` F1 = 0.000 as a classifier property would be the flattering artifact
inverted.

**Why the rare classes are this thin, and why it was not fixed:** M2-14's enriched draw
came up **31 of 60** (trigger t13 fired) and amendment 002 then dropped M2-1b, so the
enriched steps are committed in `sampling.json` and **unlabelled**. The dev set is the
random-90's first 40 and nothing else. Backfilling from the random pool was refused in code,
not by memory — it would take steps out of the half carrying the published κ to prop up the
half that does not.

---

## 5. The confusion matrix — where it fails, not just how often

Most recent dev run (n = 40; rows human, columns classifier):

| human ↓ / clf → | linear | verification | subgoal | backtrack | backward |
| --- | --- | --- | --- | --- | --- |
| **linear** (34) | **33** | 0 | 1 | 0 | 0 |
| **verification** (4) | **4** | 0 | 0 | 0 | 0 |
| **subgoal_setting** (1) | 1 | 0 | 0 | 0 | 0 |
| **backtracking** (1) | 1 | 0 | 0 | 0 | 0 |
| **backward_chaining** (0) | 0 | 0 | 0 | 0 | 0 |

**This particular run is near-degenerate** — `linear` 39 times in 40. On other runs at the
same bundle the classifier predicts `linear` 29 times and populates three other classes.
**Both behaviours are the same prompt on the same corpus**; see §3.

**The stable finding across every run is the `linear`/`verification` boundary**, and
M2-1a's blind annotator note named it before any κ existed: on `mb-08`'s repetition loop a
third of the steps open with *"Let's check:"*, and the classifier read **the marker, not the
move**. That was fixed in M2-3 by carrying `rubric.md` §4 into the prompt — the classifier
had the taxonomy and none of the five adjudicated hard cases the annotator had — and the
five false positives did not return in any of the six subsequent runs.

**Soundness is the half nobody was worried about and it is the half that works:** κ **0.848**
[0.655, 1.000] at n = 40 against a 0.625 baseline — clearing both B4 #2's 0.60 and the 0.70
asked of two humans.

---

## 6. Judge numbers, paired

| | value | n | note |
| --- | --- | --- | --- |
| **Recall, seeded errors** | **8 / 10** | 10 | triage alone — the shipped configuration |
| Recall with escalation | 7 / 10 | 10 | **worse**; see below |
| **False flags, known-good text** | **0** | 24 steps / 5 traces | the number that makes recall mean something |
| **Pooled precision (strict)** | **0.643** [0.388, 0.837] | 14 | C5.6 read literally |
| **Pooled precision (symmetric)** | **0.643** [0.388, 0.837] | 14 | ADR-012's own rule applied to both sides |
| **False flags / labelled step** | **0.000** [0.000, 0.242] | 12 | per-trace clause not measurable — §2 note ⁴ |
| **Escalation vs triage delta** | **−1 case** | 10 | 10 extra frontier calls |

**Per mutation type, as hit/miss with n — never as a percentage** (a "100%" over n = 1 is
not a percentage):

| type | caught | named correctly |
| --- | --- | --- |
| arithmetic | 2 / 3 | 2 / 3 |
| constraint_violation | 0 / 1 | 0 / 1 |
| factual | 1 / 1 | 1 / 1 |
| logical | 2 / 3 | 0 / 3 |
| unsupported_leap | 2 / 2 | 1 / 2 |

### The escalation tier was measured and it subtracts

**15 steps selected, 5 verdicts changed by the stronger model, 0 detections gained, 1
lost.** SE-06's planted `variable_swap` was flagged correctly by triage and re-judged
`sound` by the frontier tier. It recovered neither of the two cases triage already missed.

**Predictable once you read the prompt.** `escalate.md` says *"prefer `sound` when the step
is correct but terse"*, because the failure it was written against is a stronger model
echoing the cheap one's flags — *"an expensive echo"*. That instruction works, and on text
with a deliberately planted defect the same bias turns hits into misses.

**Trigger t9 fired; its pre-decided action is *publish it*. Shipped configuration:
`ESCALATION_ENABLED=0`** — already the default, so a recorded decision rather than a change.

> **The reason is not that 8 > 7.** Choosing the configuration with the better headline is
> the move this project refuses everywhere else. The reason is a measured cost with **zero
> measured benefit across ten cases**. Both configurations are published above so the claim
> is checkable rather than takeable.

**And the tier almost went unmeasured**: the M2-6 harness never read `ESCALATION_ENABLED`,
so the first "escalation enabled" run returned 9/10 against a tier that never ran. Finding 16.

### Escalation rate (ADR-012)

**8.5% selected · 4.4% escalated after the cap**, 41 arms, 270 classified steps. C4.4's
original clause (`verdict != "sound"`) selected **43.0%** on the same snapshot — **107 of
its 116 selections were `unverifiable`** — which fired t7. The clause was reading
*uncheckable* as *doubtful* on a corpus half of whose steps are legitimately unverifiable,
and `escalate.md` asks the same question under the same constraint, so escalating them
cannot resolve them. Clause split; **this is a design change to a pre-decided policy, made
under amendment 002, and it is flagged rather than buried.** Recoverable in one line.

---

## 7. Consistency

| | |
| --- | --- |
| **False flags on known-good traces** | **0 of 5** |
| **Citation-required downgrades applied** | **0** |
| Flag rule | `contradicts` only; `underdetermined` recorded, never surfaced |

The citation-required downgrade is applied **from the start** rather than held in reserve as
C4.5's escape hatch, because an accusation with no evidence is precisely the shape a
hallucinating judge produces. It fired zero times, so the before/after C4.5 asks for is
**0 → 0**: there was nothing to downgrade.

**The checker had been built, fully tested, and never called.** `build_arm` hardcoded
`"consistency": null`, so turning the flag on changed nothing anywhere. Found during M2-8,
wired, and the test that pins it goes through `build_arm` — the first version asserted on
the helper and **passed in the exact state the code was in**.

**The word "faithful" appears nowhere** in this component, its output, or any copy driven by
it. Consistency asks whether the written steps support the answer. Faithfulness asks whether
those steps are why the model produced it. B1's boundary, enforced in code.

---

## 8. Faithfulness

**0 of 48 trials flipped.** All four Appendix A.4 cue types (authority, metadata leak,
few-shot pattern, sycophancy), both problem regimes, 12 candidate pairs × 2 conditions × 5
samples, hand-adjudicated. `model_pin` committed; `test_faithfulness_pin.py` fails the build
if the pin moves without the study being re-run.

B4 #6 asked for ≥ 2 of 3 problems to reproduce. **None did, and the panel ships anyway** —
ADR-009. *"0 of 48, and here is every trial"* is a stronger artifact than *"2 of 3 flipped"*:
the second is an anecdote about a suggestible model, the first is a measurement with a
denominator that anyone can falsify at a different pin.

**A second finding sits inside the first: 3 trials produced no answer at all** — reasoning
tokens billed, zero characters returned. Asked something it cannot look up, this model does
not guess; it loops.

---

## 9. Cost of thought — reported, not graded

Appendix D #8 was never answered. **The default was taken: reporting criterion, not a
pass/fail gate**, and this section records that the default was taken (trigger t17).

**Median 5.13× · range 1.22× – 53.59×**, n = 14 items.

| tag band | items | median ratio |
| --- | --- | --- |
| `easy` | mb-01…mb-04 | 6.4× |
| `multi_step` | mb-05…mb-08, mb-11, mb-13 | 3.5× |
| `factual` + `tool_required` | mb-09, mb-10 | 18.6× |

**The 53.59× outlier is `mb-08` and it is the degenerate repetition loop**, not a hard
problem — the same trace that repeats one sentence 126 times. It is reported rather than
trimmed: the cost of thought on a trace where thinking goes nowhere is exactly the thing
this criterion exists to make visible.

**Cost is in tokens, not dollars.** `analyzer/prices.json` is dated and its per-token rates
are **null**: nobody verified current rates for these exact dated model ids, and an invented
rate would make `est_cost_usd` look measured when it was assumed. Token counts are measured
from span usage and are published. The file states exactly what to fill in to publish dollars.

---

## 10. What was changed, and when — the section that makes §§2–9 credible

| | |
| --- | --- |
| **Frozen bundle** | `e8952d4d3c51` |
| **Freeze commit** | `3e09bf3` · `calibration/labels/HELDOUT_FREEZE` |
| **Tag** | `prompts-frozen-v1` |
| **Held-out set read** | **TWICE. Both runs disclosed — see below** |
| **Prompt changelog** | `analyzer/src/rlens/prompts/CHANGELOG.md` — every cycle with κ before → after |
| **Thresholds** | `docs/decisions/ADR-012-judge-thresholds.md` |

### The held-out set was read three times. Here is every run and the reason for each.

C5.4 says the held-out set is opened once, and M2-17's card names the one legitimate
exception: *"if a second read becomes genuinely necessary — a bug in the CLI, a
mis-specified pin — that is legitimate, and **both runs appear in the report with the
reason**. The discipline is disclosure, not perfection."* This is that case.

| | run 1 | run 2 | run 3 |
| --- | --- | --- | --- |
| time (UTC) | 12:40:04Z | 12:41:40Z | 12:52Z |
| bundle | `e8952d4d3c51` | `e8952d4d3c51` | `e8952d4d3c51` |
| **n** | **140** | **50** | **50** |
| behavior κ | 0.302 [0.050, 0.534] | **0.5495495495495492** | **0.5495495495495492** |
| reason | — | CLI defect: n = 140 | join the measured auxiliary metrics |

**Runs 2 and 3 are identical to sixteen decimal places**, including the bootstrap interval
and its note that *19 of 2000 resamples were dropped as undefined*. That identity is the
point of reporting run 3 rather than hiding it: it is positive evidence that this
computation is deterministic over committed bytes and that **nothing was re-rolled**.

**Run 3's reason.** `judge_precision`, `judge_recall` and `consistency_fp_rate` were all
**measured** — by M2-7, M2-6 and M2-8 — and all sat in their own files, so `latest.json`
carried `null` and the public calibration page said *"not yet measured"* for three numbers
this project had measured. **Understating is not automatically safe**: the page was making a
false statement about the evidence, in the conservative direction. They are now read from
the artefact each task wrote — read, never recomputed, so each number has exactly one
producer.

**The defect:** `--final` scored every label row it could load — the dev 40, **plus the
held-out 50 once per annotator**. That folds the steps the prompt was tuned against into the
number whose entire purpose is to be untouched by tuning, and double-counts every held-out
step because two people labelled it. n = 140 is 40 + 50 + 50.

**What did not change between the runs.** No prompt, no model pin, no label, no report, and
no spend: `--final` reads committed files and makes **zero model calls**, so the second read
is arithmetic over the same bytes. The tag `prompts-frozen-v1` is on the commit both runs
ran against.

**Why the first number is not the safer one to quote.** 0.302 is lower, so publishing it
would look conservative. It is not conservative, it is wrong: it is a κ over a set that is
71% dev steps, reported under a heading that says held-out. **A number that flatters nobody
can still be the wrong number**, and quoting it to avoid the appearance of re-rolling would
be choosing optics over the measurement.

The fix is committed with a test that fails on the old behaviour by name
(`test_final_scores_the_heldout_set_only_and_once_per_step`), negative-tested.

### Process checks that failed, reported rather than ticked

- **P1 — IAA κ must predate the first classifier κ in commit order. IT DID NOT.** `c7e070c`
  committed the dev κ with `inter_annotator` null. P1 is one of two checks the breakdown
  says *can only be reported*, so it is reported. **It does not compromise the pass**: the
  second annotator labelled blind, both label sets were frozen before the κ was computed,
  and neither disputed step is in the dev 40.
- **M2-2's confirmation is UNSIGNED**, and all 50 of the second annotator's rows carry one
  identical `labeled_at` — the file records a single write. `calibration/README.md` had
  required this pass to be *"typed, one step at a time"*. Not evidence of anything wrong;
  evidence of **nothing**, which puts the procedural half of B4 #1 on a blank confirmation.
- **The adjudication did not happen.** Amendment 002 dropped it — it is *by discussion* and
  neither party had the time. The raw κ stands as a floor; the 2 contested steps publish
  with both readings and no resolution; `rubric.md` stays at v1 and gains no hard cases.

### Two corrections made to this project's own published conclusions

1. **ADR-010's `backtracking = 0`** was published off one run of a non-deterministic
   classifier. Twelve runs put it at 2.0%, firing 1–15 times per run. Corrected.
2. **M2-3's "cycle 3 collapsed the classifier"** was published off one run, in the same
   document that warns about exactly that. A later rebuild at the *previous* bundle
   reproduced the identical numbers. Corrected — see finding 15.

**Both are in this section deliberately.** A reviewer deciding how much to trust §§2–9
should know that this project has twice inferred a property from a single run, and has
twice caught and corrected it in writing.

### Defects found in the instrument during Month 2

- **`make calibrate` computed κ over a silently smaller set.** A degraded classifier call
  leaves the step in the report with a null label, so the join dropped it — κ over n = 32
  under a header reading *"40 labels"*. `--final` now **refuses** rather than publish a
  shrunken denominator, and `make coverage-check` asks the question in advance. This was a
  live exposure: `mb-09:thinking` carries **10 of the 50 held-out steps** and fails
  intermittently.
- **C5.4's held-out guard was keyed on a filename** while the labelling tool writes
  `<annotator>.jsonl`. Re-keyed on the draw.
- **The known-good pool was nearly re-selected after its judge had run.** M2-6 ran early and
  chose five traces; a fresh §4.4 selection picked a different five. The guard was on the
  wrong path. Moved.

---

## 11. The three C0.3 changes

Appendix D #7 asked the reviewer to acknowledge C0.3 #1, #2 and #5. **No acknowledgement was
obtained and the default was taken — the plan proceeds as written**, which the plan permits
and which amendment 002 §4 records.

| # | Change | Status |
| --- | --- | --- |
| 1 | B4 #4 is unmeasurable as written; C5.6's pooled construction replaces it | **Applied.** §6. Its second clause is separately unmeasurable — §2 note ⁴ |
| 2 | Month-2 scope additions (M2-13…M2-19) are unbudgeted in B8 | **Applied.** §12 carries the hours |
| 5 | (spent) | — |

---

## 12. The ledger — the C10.5 contingency trigger reading

| | |
| --- | --- |
| **Lead hours, cumulative** | **97.4 h** |
| **B9 allocation** | **12.0 h** |
| **Planned across M1 + M2** | 55.3 h |
| **Over planned by** | **+42.1 h** |
| **C10.5 margin** | 6.0 h |

> # The trigger fired, and it did not fire this week.
>
> It fired in **W3**. Every C14 cut lever — L1, L2, L3, L4, L6 — is already applied. The
> contingency and the calendar are the only instruments left.

**From 16 Sep the work is agent-executed** (amendment 002). Agent rows are booked at **0.0
h** and prefixed `[AGENT]`, so **Lead hours freeze at 97.4 h**. That is not a saving: it is
the C10.1 trigger counting *Lead* hours, and booking agent work there would destroy the only
signal this section gives you.

**What is still asked of a human — two things, both minutes:**

1. **Accept or correct amendment 002**, in particular its dropped rows (M2-1b, M2-15,
   M2-2's adjudication, M3-5b) and its §2 boundary.
2. **U4 — the C10.1 contingency conversation** with the delivery manager. 97.4 h against 12,
   every cut lever spent. **This is the only row on any board that no amount of code
   advances.**

---

## Appendix — the four criteria that stopped being measurements

Amendment 002 records these; they are repeated here so the gate does not have to go looking.

| | Why it cannot be measured | What ships instead |
| --- | --- | --- |
| **B4 #9 / E12** — 5 walkthrough testers | No testers exist. A reader who can open the source is not a naive viewer | `walkthrough-notes.md` as a written, unexecuted protocol, with the pass mark fixed in advance |
| **E13** — peer runbook dry-run | Requires someone who did not write it | An agent cold-run, offered as a partial substitute and explicitly not a pass |
| **C15.1 #10** — lit-survey sign-off | A sign-off is a person putting their name to a claim | A review report. Not a signature |
| **B4 #4's per-trace clause** | Needs M2-15's full labelling | A per-labelled-step rate, with the conversion stated rather than performed |

**A model cannot supply the human half of a human-vs-model measurement.** B4 #1, #2, #4 and
#5 all read the human label file; substituting the agent there would make four criteria
circular in one move, and the circularity would be invisible in the published artifact. That
boundary is amendment 002 §2, and it is the reason this report has shortfalls in it rather
than numbers.
