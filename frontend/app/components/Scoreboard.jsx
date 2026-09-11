"use client";

import { ARM_LABEL } from "../lib/labels";

/**
 * FE-3 — per-arm metrics, the verdict line, and the failed-arm column.
 *
 * **I3 is the whole design of this component.** "Every score renders next to its own error
 * bars" is not a caption rule — it is why `Soundness` is a single cell containing both the
 * number and its precision/recall, rather than a number here and a footnote elsewhere. A
 * footnote can be scrolled past; a cell cannot.
 *
 * Every field of `measurement_context` is null until M2-17 runs the calibration, so today
 * that cell reads **"not yet measured"** in warning colour. It does not read 0, and it does
 * not disappear — an absent row is indistinguishable from a good one, and a reviewer
 * reading a soundness score with nothing beside it will assume somebody checked.
 */

function fmt(v, digits = 0) {
  if (v === null || v === undefined) return "—";
  return typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: digits }) : v;
}

function Soundness({ arm, context }) {
  const score = arm.metrics?.soundness_score;
  if (score === null || score === undefined) {
    return <span className="mono">—</span>;
  }
  const precision = context?.judge_precision;
  const recall = context?.judge_recall;
  const measured = precision !== null && precision !== undefined;
  return (
    <span className="withbars">
      <span className="mono">{(score * 100).toFixed(0)}%</span>
      <span className={measured ? "bars" : "bars unmeasured"}>
        {measured
          ? `judge P ${(precision * 100).toFixed(0)}% · R ${(recall * 100).toFixed(0)}%`
          : "judge accuracy not yet measured"}
      </span>
    </span>
  );
}

export default function Scoreboard({ report, arms }) {
  const context = report.measurement_context;
  const board = report.scoreboard ?? {};
  const unmeasured = !context || context.judge_precision === null;

  return (
    <section className="scoreboard">
      <header>
        <h2>Scoreboard</h2>
        {board.verdict_line ? (
          <p className="verdictline">{board.verdict_line}</p>
        ) : (
          <p className="verdictline">
            {board.cost_of_thought_ratio
              ? `Extended thinking spent ${board.cost_of_thought_ratio}× the reasoning tokens of Direct, and the accuracy delta is ${board.accuracy_delta_pp ?? 0} pp.`
              : "No verdict line for this item yet — M2-10b writes them from a template and a measured fact."}
          </p>
        )}
      </header>

      <div className="sb-scroll">
        <table className="sb">
          <thead>
            <tr>
              <th>Arm</th>
              <th>Answer</th>
              <th>Reasoning tokens</th>
              <th>Steps</th>
              <th>Flagged</th>
              <th>Soundness</th>
            </tr>
          </thead>
          <tbody>
            {arms.map((arm) => {
              // The failed-arm column C4.10 asks for. Present, named, and not silently
              // dropped: an absent arm is indistinguishable from one nobody ran (B6.5).
              if (arm.status === "failed") {
                return (
                  <tr key={arm.strategy}>
                    <td>{ARM_LABEL[arm.strategy] ?? arm.strategy}</td>
                    <td className="failed" colSpan={5}>
                      arm failed — no trace, no metrics. The other arms are unaffected.
                    </td>
                  </tr>
                );
              }
              return (
                <tr key={arm.strategy}>
                  <td>{ARM_LABEL[arm.strategy] ?? arm.strategy}</td>
                  <td className="mono">
                    {arm.final_answer || "—"}{" "}
                    <span
                      className={
                        "chip " +
                        (arm.correct === true ? "ok" : arm.correct === false ? "bad" : "unknown")
                      }
                    >
                      {arm.correct === true ? "correct" : arm.correct === false ? "wrong" : "unparsed"}
                    </span>
                  </td>
                  <td className="mono">{fmt(arm.metrics?.reasoning_tokens)}</td>
                  <td className="mono">{arm.steps.length}</td>
                  <td className="mono">{fmt(arm.metrics?.flagged_step_count)}</td>
                  <td>
                    <Soundness arm={arm} context={context} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {unmeasured ? (
        <p className="i3note">
          <b>No soundness score on this page has been calibrated yet.</b> The judge&apos;s
          precision and recall are measured once, at M2-17, against human labels — until then
          every field of <code>measurement_context</code> is null and this row says so. I3:
          a score without its error bars is an assertion, and this page does not make
          assertions.
        </p>
      ) : null}
    </section>
  );
}
