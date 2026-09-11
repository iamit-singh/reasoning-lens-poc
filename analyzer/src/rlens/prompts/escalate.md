<!--
C4.4 / Appendix A.2. The frontier tier. Owner: M2-5.

Part of `PROMPT_BUNDLE_VERSION`.

THE FAILURE THIS PROMPT IS WRITTEN AGAINST: a stronger model, told that a cheaper one
flagged these steps, agrees with the flag. That is not a second opinion, it is an expensive
echo -- and it would make the escalation tier look like it works while making the flagged
set strictly larger. So the prompt says "re-judge independently" and it says "prefer sound
when the step is correct but terse", because terseness is what the cheap pass most often
mistakes for a defect.

The first-pass verdict is DELIBERATELY NOT SHOWN. Appendix A.2's sketch mentions that a
cheaper model flagged them; naming the specific verdict per step would anchor the answer
to the thing we are trying to check.

Placeholders: {item_prompt} {context_block} {steps_block} {step_id_list} {n_steps}
-->

A cheaper model flagged the steps below as possibly unsound, or was unsure about them.
**Re-judge each one independently**, using the full preceding context supplied.

You are not told what the cheaper model decided, and you should not try to infer it. Judge
each step on its own merits.

**Prefer `sound` when the step is correct but terse.** A step that skips working you can
verify yourself is sound. A step is `unsound` only when you can name the specific defect:
the arithmetic is wrong, the inference does not follow, or it contradicts something already
established. A step is `unverifiable` when it asserts something it neither derives nor
cites.

Judge each step GIVEN ONLY the steps that precede it. An error carried forward correctly
from an earlier wrong step is not itself a new error — the step that introduced it is where
the defect is.

Do NOT consider whether the final answer is correct. You are not told whether it is.

PROBLEM: {item_prompt}

{context_block}STEPS TO RE-JUDGE:
{steps_block}

Return JSON only — no prose, no markdown fence — with exactly {n_steps} rows, one per step
above, using these `step_id` values exactly as written:
{step_id_list}

{"steps":[{"step_id": "...", "verdict": "...", "validity_confidence": 0.0,
"error_type": null, "rationale": "..."}]}

`verdict` is one of `sound`, `unsound`, `unverifiable`. `error_type` is one of
`arithmetic`, `logical`, `factual`, `constraint_violation`, `unsupported_leap` when the
verdict is `unsound`, and null otherwise. `rationale` is at most 200 characters and names
the specific defect rather than a general impression.
