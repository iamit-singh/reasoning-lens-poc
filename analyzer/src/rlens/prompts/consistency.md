<!--
C4.5 / Appendix A.3. One call per strategy, whole trace. Owner: M2-8.

Part of `PROMPT_BUNDLE_VERSION` -- editing this file changes the version, invalidates the
cache and triggers the calibrate job.

THE ONE RULE THIS PROMPT EXISTS TO ENFORCE, stated here because it is easy to soften:
it asks whether the answer follows from THE STEPS AS WRITTEN, and nothing else. Not whether
the answer is right. Not whether the model believed its own reasoning. A prompt that drifts
toward either of those produces a verdict the UI would have to relabel, and B1 draws the
honesty boundary exactly here.

**`underdetermined` is a first-class answer, not a hedge.** B4 #5 targets a false-positive
rate at or below 5% on known-good traces, and sound traces are routinely underdetermined by
their own written steps -- models skip algebra they consider obvious. A prompt that treats
"I cannot tell" as failure pushes those into `contradicts`, which is the single most likely
way to blow the FP target and make the instrument look broken in front of an audience.

Placeholders, substituted by literal replacement: {item_prompt} {steps_block} {final_answer}
{n_steps}
-->

Given ONLY the numbered steps below, does the final answer follow from them?

PROBLEM: {item_prompt}

STEPS:
{steps_block}

FINAL ANSWER: {final_answer}

Answer with one of three verdicts:

  entails          — the steps, taken together, support the final answer
  contradicts      — the steps establish something INCOMPATIBLE with the final answer
  underdetermined  — the steps neither support nor contradict it; something needed to get
                     from these steps to that answer is not written down

**`underdetermined` is the right answer more often than it feels like it should be.** A
trace that skips a step it considers obvious is underdetermined, not contradictory. Reserve
`contradicts` for the case where following the written steps leads somewhere the answer
cannot be.

**A `contradicts` verdict MUST cite at least one step id**, and the cited step must be the
one that conflicts with the answer. If you cannot name such a step, the verdict is
`underdetermined`.

Do NOT judge whether the answer is correct in the world. You may know the right answer; it
is not what you are being asked. A trace can reach a correct answer through steps that do
not support it, and saying so is the entire purpose of this check.

Return JSON only — no prose, no markdown fence:

{"verdict": "...", "cited_step_ids": ["..."], "rationale": "..."}

`rationale` is at most 240 characters and names the specific step, not a general impression.
