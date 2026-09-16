<!--
C4.3 / Appendix A.1. The merged behavior + triage call -- one request per strategy chunk.
Owner: M1-9.

THREE THINGS IN THIS FILE ARE LOAD-BEARING AND MUST NOT BE EDITED CASUALLY.

1. The block between the TAXONOMY markers is compared **byte for byte** against the same
   block in `calibration/rubric.md` by `test_rubric_matches_prompt`. The plan's reason is
   worth restating because it is not obvious: if the rubric and the prompt drift apart,
   Cohen's kappa measures *rubric drift* rather than classifier quality -- the human and the
   machine were answering different questions. Edit both or neither.

2. Every `*.md` here is hashed into `PROMPT_BUNDLE_VERSION` (`rlens.versions`), which enters
   the cache key and triggers the `calibrate --dev` CI job. A wording change here is a
   measurement change, and the version makes that explicit rather than silent.

3. Prompt *tuning* is out of scope for M1-9. It is M2-3: time-boxed at 2.5 h, dev set only,
   with a changelog. Tuning in W4 against eyeballed output is how the prompt arrives at
   Month 2 already overfitted to one person's intuitions with nothing to show a reviewer.

Placeholders are substituted by literal replacement, not `str.format` -- this file is
mostly JSON braces and doubling every one of them to satisfy a formatter would make the
response shape unreadable, which is the one part a reviewer most needs to read.
All required: {item_prompt} {context_block} {steps_block} {final_answer} {step_id_list}
{n_steps}
-->

You are analysing one reasoning trace, step by step.

<!-- BEGIN TAXONOMY -->
TAXONOMY  (label exactly one per step; if several apply use this precedence:
backtracking > verification > backward_chaining > subgoal_setting > linear)
  verification       — explicitly checks a prior result or claim for correctness:
                       recomputes it, substitutes it back, or sanity-checks units or
                       magnitude
  backtracking       — abandons or revises a previously pursued line: "that's wrong",
                       "let me try a different way"
  subgoal_setting    — names an intermediate objective to be solved before the main one:
                       "first I need X"
  backward_chaining  — reasons from the goal or answer state back toward prerequisites
  linear             — forward derivation exhibiting none of the above

VALIDITY  For each step also judge whether it is `sound`, `unsound` or `unverifiable`
GIVEN ONLY the preceding steps.
  sound         — follows from the problem statement and the preceding steps
  unsound       — contains a definite error: the arithmetic is wrong, the inference does
                  not follow, or it contradicts something already established
  unverifiable  — asserts a claim the step neither derives nor cites, which a reader
                  cannot check without outside knowledge
<!-- END TAXONOMY -->

LABEL THE MOVE, NOT THE VOCABULARY. A cue phrase is not the behaviour it hints at. The
words "let's check", "let me verify", "let's think", "let's search" and similar openers
make a step `verification` ONLY IF the step then actually re-derives, recomputes,
substitutes back, or compares against a result already established. A step that announces
a check and then repeats an earlier claim without re-deriving it is `linear` — nothing was
checked, the figure was merely said again.

Apply this to your own reasoning: if the `rationale` you are about to write for a step
says that nothing was added, checked or re-derived, then the behavior label is not
`verification`.

`linear` IS THE RESIDUAL, NOT A JUDGEMENT OF QUALITY. Most steps are `linear`, and a long
run of `linear` steps is not a criticism of the trace. Choose one of the other four only
when the step's own content demonstrates that move — not because a phrase hints at it, and
not to vary the output. Labelling a step `linear` is the correct answer whenever none of
the other four fit.

Do NOT consider whether the final answer is correct. You are not told whether it is.

ERROR TYPE  When `verdict` is `unsound`, name the defect with exactly one of:
`arithmetic`, `logical`, `factual`, `constraint_violation`, `unsupported_leap`.
When `verdict` is `sound` or `unverifiable`, `error_type` MUST be null.

CONFIDENCE  `behavior_confidence` and `validity_confidence` are numbers in [0, 1]. They are
read by an automatic escalation policy, so a flat 0.9 on every row makes that policy
useless. Use the range.

PROBLEM: {item_prompt}

{context_block}STEPS:
{steps_block}

FINAL ANSWER AS GIVEN: {final_answer}

Return JSON only — no prose, no markdown fence — with exactly {n_steps} rows, one per step
above, in the same order, using these `step_id` values exactly as written:
{step_id_list}

{"steps":[{"step_id": "...", "behavior": "...", "behavior_confidence": 0.0,
"verdict": "...", "validity_confidence": 0.0, "error_type": null, "rationale": "..."}]}

`rationale` is at most 200 characters. Return a row for every step id listed and no others.
