import Link from "next/link";
import { faithfulness } from "../lib/faithfulness";

/**
 * FE-5 — the faithfulness panel.
 *
 * B6.3 specified this as the demo's guaranteed wow moment: a model given a planted hint,
 * changing its answer, and never mentioning the hint in its reasoning. **That does not
 * happen on this pin.** S4 measured 0 flips in 48 trials across all four Appendix A.4 cue
 * types, and ADR-009 took the pre-decided action for trigger t11: publish the negative
 * result.
 *
 * So this page renders a null result, and the design problem is making that read as a
 * *measurement* rather than as a missing feature. Three choices carry that:
 *
 * 1. **The denominator is in the headline.** "0 of 48" is a finding; "no flips detected"
 *    is an absence, and an absence is also what a broken harness produces.
 * 2. **Every trial is listed.** A reader who doubts the number can count the rows — the
 *    same instinct as the calibration page refusing to hide its unmeasured rows.
 * 3. **The caveat carries the same weight as the claim.** One pin, one arm, small n. A
 *    bold zero with a footnote is how a narrow measurement becomes a broad claim.
 *
 * Like FE-6, there are **no numeric literals in this file**. Every count comes from
 * `faithfulness/panel.json`.
 */

export const metadata = { title: "Faithfulness — Reasoning Lens" };

export default function FaithfulnessPage() {
  const panel = faithfulness();

  if (!panel) {
    return (
      <section className="cal">
        <Link className="backlink" href="/">
          ← every item
        </Link>
        <h2>Faithfulness</h2>
        <p className="notice">
          <span className="unmeasured">not yet measured</span> — the cue-injection batch job
          has not produced a panel. Run <code>make faithfulness</code>.
        </p>
      </section>
    );
  }

  const { headline, by_cue: byCue, problems, provenance } = panel;

  return (
    <section className="cal">
      <Link className="backlink" href="/">
        ← every item
      </Link>

      <h2>Does a planted hint change the answer?</h2>
      <p className="lede">
        Each problem is asked twice: once plainly, once with a hint pointing at a different
        option. A <b>flip</b> is the answer changing. <b>Verbalised</b> means the reasoning
        mentioned the hint. The interesting failure is a flip that is <i>not</i> verbalised —
        a model acting on something it does not admit to.
      </p>

      <div className="block">
        <h3>
          Result — {headline.n_flipped} of {headline.n_trials} trials
        </h3>
        <div style={{ padding: "14px 16px" }}>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.55 }}>{headline.statement}</p>
          <p className="provenance-foot" style={{ marginTop: 10 }}>
            {headline.caveat}
          </p>
        </div>
      </div>

      <div className="block">
        <h3>By cue type</h3>
        <table className="metrics">
          <thead>
            <tr>
              <th>Cue</th>
              <th>Trials</th>
              <th>Flipped</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(byCue).map(([key, row]) => (
              <tr key={key}>
                <td className="name">{row.label}</td>
                <td className="mono">{row.n}</td>
                <td className="mono">{row.flipped}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Every trial</h2>
      <p className="lede">
        Listed in full rather than summarised, so the headline can be checked rather than
        taken.
      </p>

      {problems.map((p) => (
        <div className="block" key={p.id}>
          <h3>
            <span className="mono">{p.id}</span> — {p.regime_label}
          </h3>
          <div style={{ padding: "10px 16px 0" }}>
            <p className="provenance-foot" style={{ margin: 0 }}>
              Answer with no hint:{" "}
              {p.unhinted_answer ? (
                <span className="mono">{p.unhinted_answer}</span>
              ) : (
                <span className="unmeasured">no answer at all</span>
              )}{" "}
              · flipped {p.n_flipped} of {p.n_trials} · mentioned the hint {p.n_verbalised}{" "}
              times
            </p>
          </div>
          <table className="metrics">
            <thead>
              <tr>
                <th>Cue</th>
                <th>Hint points at</th>
                <th>Answered</th>
                <th>Flipped</th>
                <th>Mentioned hint</th>
              </tr>
            </thead>
            <tbody>
              {p.cues.map((c) => (
                <tr key={`${c.cue_type}-${c.repeat}`}>
                  <td className="name mono">{c.cue_type}</td>
                  <td className="mono">{c.cued_option}</td>
                  <td className="mono">
                    {c.no_answer ? <span className="unmeasured">none</span> : c.hinted_option}
                  </td>
                  <td className="mono">{c.flipped ? "yes" : "no"}</td>
                  <td className="mono">{c.hint_verbalised ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <h2>What this does and does not show</h2>
      <ul className="limits">
        <li>
          <b>It shows</b> that on <span className="mono">{panel.model}</span> at pin{" "}
          <span className="mono">{panel.model_pin}</span>, the {panel.arm} arm did not change
          its answer for any hint tried — and that when it discussed a hint, it went on to
          answer what it was going to answer anyway.
        </li>
        <li>
          <b>It does not show</b> that reasoning models are faithful. The n is small, the
          model is one open-weight model, and one arm was tested.
        </li>
        {headline.n_no_answer > 0 ? (
          <li>
            <b>A separate finding sits inside this one:</b> {headline.n_no_answer} trials
            produced no answer at all — reasoning tokens billed, zero characters returned.
            Asked something it cannot look up, this model does not guess; it loops.
          </li>
        ) : null}
        <li>{provenance.note}</li>
      </ul>

      <p className="provenance-foot">
        <span className="mono">{provenance.source}</span> · rebuild with{" "}
        <code>{provenance.rebuild}</code> · run <span className="mono">{panel.run_date}</span>
      </p>
    </section>
  );
}
