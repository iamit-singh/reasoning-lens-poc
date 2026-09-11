"use client";

import { ARM_LABEL } from "../lib/labels";

/**
 * FE-2 — the annotated trace renderer.
 *
 * Every definition on this surface arrives as a prop, parsed from `calibration/rubric.md` at
 * build time. Nothing here restates a rule. The rubric is already byte-identical to the
 * classifier prompt (`check_rubric_drift.sh` fails the build otherwise), so a reviewer
 * hovering a tag reads the same sentence the annotator read and the model was given.
 */

function BehaviorTag({ label, definitions }) {
  if (!label) {
    return (
      <span className="tag-b none" title="This step carries no label — see the banner above.">
        unannotated
      </span>
    );
  }
  return (
    <span className={`tag-b ${label}`} title={definitions[label] ?? label}>
      {label.replace(/_/g, " ")}
    </span>
  );
}

function ValidityTag({ validity, definitions }) {
  if (!validity) return null;
  const { verdict, confidence, error_type } = validity;
  const title = `${definitions[verdict] ?? verdict}\n\nconfidence ${confidence.toFixed(2)}${
    error_type ? `\nerror type: ${error_type}` : ""
  }`;
  return (
    <span className={`tag-v ${verdict}`} title={title}>
      {verdict}
      {error_type ? ` · ${error_type}` : ""}
    </span>
  );
}

/** The states C4.10 names for this component, each said in words rather than implied. */
function Banner({ arm }) {
  if (arm.status === "failed") {
    return (
      <p className="banner stop">
        <b>This arm failed.</b> The provider did not return after its retry, so there is no
        trace to show. The other arms are unaffected — that is deliberate (B6.5).
      </p>
    );
  }
  if (arm.degraded?.reason === "classifier_parse_failure") {
    return (
      <p className="banner loop">
        <b>Rendered unannotated.</b> The classifier did not return a conforming row for every
        step, twice. The steps below are the model&apos;s real reasoning; the labels are
        absent because inventing one would be indistinguishable from a real one.
      </p>
    );
  }
  if (arm.degraded) {
    return (
      <p className="banner loop">
        <b>Degraded:</b> {arm.degraded.reason.replace(/_/g, " ")}. The trace is complete; a
        later stage did not run.
      </p>
    );
  }
  if (arm.trace_quality === "provider_summarised") {
    return (
      <p className="banner">
        <b>Provider-summarised.</b> This text is the provider&apos;s summary of the
        reasoning, not the reasoning itself. It is real text and it is second-hand, and
        those are different things.
      </p>
    );
  }
  if (arm.trace_quality === "partial") {
    return (
      <p className="banner">
        <b>Partial trace.</b> Either the arm timed out, or it produced reasoning and no
        visible answer.
      </p>
    );
  }
  return null;
}

function Steps({ arm, definitions }) {
  if (!arm.steps.length) {
    return (
      <p className="empty">
        {arm.strategy === "direct"
          ? "No reasoning steps — which is what the Direct arm is for. It answers without showing work, and an empty trace here is the measurement, not a gap."
          : "No steps in this trace."}
      </p>
    );
  }
  return (
    <ol className="steps">
      {arm.steps.map((step, i) => {
        const flagged = step.validity && step.validity.verdict === "unsound";
        return (
          <li key={step.step_id} className={flagged ? "step flagged" : "step"}>
            <div className="head">
              <span className="ord mono">{i + 1}</span>
              <BehaviorTag label={step.behavior?.label} definitions={definitions.behaviors} />
              <ValidityTag validity={step.validity} definitions={definitions.soundness} />
              {step.kind !== "thought" ? <span className="kindchip">{step.kind}</span> : null}
            </div>
            <div className="text">{step.text}</div>
            {step.validity?.rationale ? (
              <div className="why">{step.validity.rationale}</div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export default function Trace({ arms, definitions }) {
  return (
    <section className="trace">
      <h2>The reasoning, step by step</h2>
      <p className="hint">
        Each step carries what kind of move it is and whether it follows from the steps before
        it. Hover a tag for its definition — the same sentence the human annotator reads and
        the classifier is given, because all three come from one file.
      </p>

      <div className="legend">
        <span className="lbl">Behaviours:</span>
        {Object.keys(definitions.behaviors).map((label) => (
          <BehaviorTag key={label} label={label} definitions={definitions.behaviors} />
        ))}
      </div>

      <div className="tracepanes">
        {arms.map((arm) => (
          <article key={arm.strategy} className="tracepane">
            <header>
              <h3>{ARM_LABEL[arm.strategy] ?? arm.strategy}</h3>
              <span className="kindchip">
                {arm.steps.length} step{arm.steps.length === 1 ? "" : "s"} ·{" "}
                {arm.trace_quality}
              </span>
            </header>
            <Banner arm={arm} />
            <Steps arm={arm} definitions={definitions} />
          </article>
        ))}
      </div>
    </section>
  );
}
