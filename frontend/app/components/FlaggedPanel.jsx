"use client";

import { ARM_LABEL, cleanRationale } from "../lib/labels";

/**
 * FE-4 — the flagged-step side panel.
 *
 * Four things per flag, and C4.10 names all four: the rubric verdict, the error type, the
 * **escalated / not escalated** badge, and the consistency warning.
 *
 * The escalated badge is the one that is easy to leave out, because in Month 1 it is always
 * false — the frontier tier does not exist until M2-5. **It renders anyway, in both
 * states.** B6.2 step 5 is specifically about a reviewer being able to see which flags were
 * double-checked by a better model and which carry only the cheap verdict, and a badge that
 * appeared later would be a badge nobody had designed a layout for.
 */

function Escalation({ validity }) {
  if (validity.escalated) {
    return (
      <span
        className="chip ok"
        title="A stronger model re-judged this step and its verdict replaced the first-pass one (C4.4)."
      >
        re-checked by the stronger model
      </span>
    );
  }
  return (
    <span
      className="chip unknown"
      title="Only the first-pass judge saw this step. The escalation tier either did not select it or has not run."
    >
      first-pass verdict only
    </span>
  );
}

function Consistency({ arm }) {
  const c = arm.consistency;
  if (!c) {
    return (
      <p className="consistency" style={{ background: "var(--sunk)", color: "var(--ink-2)" }}>
        <b>Whole-trace consistency not checked.</b> The checker is M2-8. This asks only
        whether the answer follows from these steps — never whether the answer is right in
        the world, which is a different question and is answered by the checker above.
      </p>
    );
  }
  if (c.verdict === "contradicts") {
    return (
      <p className="consistency">
        <b>The answer does not follow from these steps.</b> {cleanRationale(c.rationale)}
        {c.cited_step_ids?.length ? (
          <>
            {" "}
            Cited: <span className="mono">{c.cited_step_ids.join(", ")}</span>.
          </>
        ) : null}
      </p>
    );
  }
  if (c.verdict === "underdetermined") {
    return (
      <p className="consistency" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>
        <b>The steps neither support nor contradict the answer.</b> {cleanRationale(c.rationale)}
      </p>
    );
  }
  return (
    <p className="consistency clear">
      <b>The answer follows from these steps.</b> {cleanRationale(c.rationale)}
    </p>
  );
}

export default function FlaggedPanel({ arms }) {
  const flags = arms.flatMap((arm) =>
    (arm.steps ?? [])
      .filter((s) => s.validity && s.validity.verdict === "unsound")
      .map((step) => ({ arm, step }))
  );

  return (
    <section className="flagged-panel">
      <h2>Flagged steps</h2>
      <p className="hint">
        Steps the judge called <b>unsound</b> — a definite error it can point to, judged
        against the steps before it and not against whether the final answer turned out
        right.
      </p>

      {flags.length === 0 ? (
        <p className="notice">
          No step on this item was judged unsound. That is a result, not an empty state — and
          on an uncalibrated judge it is a result whose false-negative rate is unmeasured
          until M2-17.
        </p>
      ) : (
        flags.map(({ arm, step }) => (
          <article key={step.step_id} className="flag">
            <div className="head">
              <span className={`tag-v ${step.validity.verdict}`}>{step.validity.verdict}</span>
              {step.validity.error_type ? (
                <span className="chip bad">{step.validity.error_type.replace(/_/g, " ")}</span>
              ) : null}
              <Escalation validity={step.validity} />
              <span className="where mono">
                {ARM_LABEL[arm.strategy] ?? arm.strategy} · {step.step_id}
              </span>
            </div>
            <div className="quote">{step.text}</div>
            {step.validity.rationale ? (
              <p className="rationale">{cleanRationale(step.validity.rationale)}</p>
            ) : null}
            <dl>
              <dt>judge confidence</dt>
              <dd className="mono">{step.validity.confidence.toFixed(2)}</dd>
              <dt>behaviour</dt>
              <dd>{step.behavior?.label?.replace(/_/g, " ") ?? "unannotated"}</dd>
            </dl>
          </article>
        ))
      )}

      {arms.map((arm) => (
        <div key={arm.strategy}>
          <p className="where mono" style={{ marginTop: 14, marginBottom: 2 }}>
            {ARM_LABEL[arm.strategy] ?? arm.strategy}
          </p>
          <Consistency arm={arm} />
        </div>
      ))}
    </section>
  );
}
