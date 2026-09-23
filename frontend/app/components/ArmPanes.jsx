"use client";

import { useState } from "react";
import { ARM_LABEL } from "../lib/labels";

function Verdict({ arm }) {
  if (arm.status === "failed") return <span className="chip bad">arm failed</span>;
  if (arm.degraded) return <span className="chip degraded">{arm.degraded.reason}</span>;
  // `correct` is true | false | null, and null is NOT a quiet false: it means the answer
  // could not be parsed. M1-5 paid for that distinction and the UI must not undo it.
  if (arm.correct === true) return <span className="chip ok">correct</span>;
  if (arm.correct === false) return <span className="chip bad">wrong</span>;
  return <span className="chip unknown">unparsed</span>;
}

function num(v) {
  return v === null || v === undefined ? "—" : v.toLocaleString();
}

/**
 * Plain-language framing for an arm with nothing to score (E12 queue #1).
 *
 * `unparsed` is the tool's word for its own parser and `partial` is its word for its own
 * capture, and the heuristic walkthrough review found the two together invite the reading
 * *"the website failed to read that one"* — on the arrival screen, over the single best
 * piece of evidence in the corpus for the thing this project is actually claiming. A naive
 * reader has two readings available and **the more natural one discounts the finding as a
 * defect in the demo**.
 *
 * So the distinction is stated in the reader's language rather than the schema's. It is
 * **derived from the arm**, never asserted: the two cases are genuinely different claims —
 * the model stated nothing at all, versus the model stated something this pipeline could
 * not read as a comparable value — and only the first of them is a result. Saying the first
 * where the second is true would be exactly the overclaim `featured()` refuses one file
 * over.
 *
 * Deliberately NOT a rewrite of the `unparsed` chip: `correct === null` is the schema's
 * truth, M1-5 paid for the distinction, and a chip that said "no answer" would be the UI
 * quietly deciding which of the two cases it was.
 */
function NoAnswerNote({ arm }) {
  if (arm.correct !== null || arm.status === "failed") return null;
  const stated = Boolean(arm.final_answer);
  const tokens = arm.metrics?.reasoning_tokens;
  return (
    <p className="noanswer">
      {stated ? (
        <>
          The model gave an answer, but not in a form this pipeline could read as a
          comparable value — so it is left unscored rather than counted wrong.
        </>
      ) : (
        <>
          The model never stated an answer. It ran {arm.steps.length.toLocaleString()} steps
          {tokens ? <> and spent {tokens.toLocaleString()} reasoning tokens</> : null} and
          stopped without one. <strong>Nothing was lost in the reading of it</strong> — there
          was no answer to read.
        </>
      )}
    </p>
  );
}

/**
 * The three arms, side by side above 768px and **tabbed below it** (C4.10, FE-1).
 *
 * Tabs rather than a horizontal scroll because the comparison is the product: three columns
 * squeezed to 90px each on a phone show three answers nobody can read, whereas one readable
 * pane and two taps preserves what the surface is for.
 *
 * The tab bar is rendered in both modes and hidden by CSS above the breakpoint, so there is
 * no layout shift and no JavaScript measuring the viewport — which also means the static
 * export is correct before hydration.
 */
export default function ArmPanes({ arms }) {
  const [active, setActive] = useState(arms[0]?.strategy ?? null);

  return (
    <>
      <div className="tabbar" role="tablist" aria-label="Strategy arms">
        {arms.map((arm) => (
          <button
            key={arm.strategy}
            role="tab"
            className="tab"
            aria-selected={arm.strategy === active}
            onClick={() => setActive(arm.strategy)}
          >
            {ARM_LABEL[arm.strategy] ?? arm.strategy}
          </button>
        ))}
      </div>
      <div className="panes">
        {arms.map((arm) => (
          <section
            key={arm.strategy}
            className="pane"
            data-tabbed={arm.strategy === active ? "shown" : "hidden"}
          >
            <h3>{ARM_LABEL[arm.strategy] ?? arm.strategy}</h3>
            <Verdict arm={arm} />
            <p className="answer mono">{arm.final_answer || "— no answer —"}</p>
            <NoAnswerNote arm={arm} />
            <dl>
              <dt>reasoning tokens</dt>
              <dd className="mono">{num(arm.metrics?.reasoning_tokens)}</dd>
              <dt>steps</dt>
              <dd className="mono">{arm.steps.length}</dd>
              <dt>trace</dt>
              <dd>{arm.trace_quality}</dd>
              {arm.budget_bound ? (
                <>
                  <dt>budget</dt>
                  <dd>
                    <span className="chip unknown">bound</span>
                  </dd>
                </>
              ) : null}
            </dl>
          </section>
        ))}
      </div>
    </>
  );
}
