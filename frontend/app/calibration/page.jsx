import Link from "next/link";
import { calibration } from "../lib/calibration";

/**
 * FE-6 — the calibration and limitations page.
 *
 * **Every number on this page comes out of `calibration/results/latest.json`.** There are no
 * numeric literals in this file and there must never be: E9 is checked by a grep over this
 * source in Month 3, and the claim the page makes — *these are the numbers we measured* — is
 * worth exactly as much as that constraint is worth.
 *
 * A null renders as "not yet measured", in warning colour, with its row intact. It does not
 * render as 0 and the row does not disappear. That is I3, and on this page it is not a
 * detail: a calibration page that hid its unmeasured rows would be a calibration page
 * claiming to be complete.
 */

const ROWS = [
  {
    key: "classifier_kappa_heldout",
    name: "Classifier agreement with a human — held-out",
    sub: "Cohen's kappa on the sealed set, read once, at a frozen prompt bundle. This is the published headline.",
  },
  {
    key: "classifier_kappa_dev",
    name: "Classifier agreement with a human — dev",
    sub: "The set the prompt was tuned against. The gap between this and the held-out figure is the overfitting reading.",
  },
  {
    key: "majority_class_baseline",
    name: "Majority-class baseline",
    sub: "What an annotator would score by labelling every step with the most common class. Kappa is unreadable without it.",
  },
  {
    key: "judge_precision",
    name: "Judge precision",
    sub: "Of the steps the judge flagged as unsound, the share a human agreed were unsound.",
  },
  {
    key: "judge_recall",
    name: "Judge recall",
    sub: "Of the errors deliberately seeded into known-good traces, the share the judge caught.",
  },
  {
    key: "consistency_fp_rate",
    name: "Consistency false-positive rate",
    sub: "How often a trace that does support its answer is reported as contradicting it.",
  },
];

function Value({ v }) {
  if (v === null || v === undefined) {
    return <span className="unmeasured">not yet measured</span>;
  }
  if (typeof v === "object") {
    const ci =
      v.ci_low === null || v.ci_low === undefined
        ? v.note || "interval not computable"
        : `${v.ci_low.toFixed(2)} – ${v.ci_high.toFixed(2)}`;
    return (
      <span className="withbars">
        <span className="mono">{v.value === null ? "undefined" : v.value.toFixed(2)}</span>
        <span className="bars">
          n = {v.n} · 95% CI {ci}
        </span>
      </span>
    );
  }
  return <span className="mono">{String(v)}</span>;
}

export default function CalibrationPage() {
  const data = calibration();

  return (
    <section className="cal">
      <Link className="backlink" href="/">
        ← every item
      </Link>

      <h2>Calibration and limitations</h2>
      <p className="lede">
        This page publishes how well the instrument agrees with a human, whatever that turns
        out to be. It renders <code>calibration/results/latest.json</code> verbatim — no
        number on this page is written into the page.
      </p>

      {!data ? (
        <p className="notice">
          No calibration results in this build. Run <code>make calibrate</code>.
        </p>
      ) : (
        <>
          <div className="block">
            <h3>Measured</h3>
            <table className="metrics">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.key}>
                    <td className="name">
                      {row.name}
                      <small>{row.sub}</small>
                    </td>
                    <td>
                      <Value v={data.measurement_context?.[row.key]} />
                    </td>
                  </tr>
                ))}
                <tr>
                  <td className="name">
                    Inter-annotator agreement
                    <small>
                      Two people, given only the written rubric and no discussion. Not
                      computable with one annotator — not harder, not noisier: not computable.
                    </small>
                  </td>
                  <td>
                    <Value v={data.inter_annotator?.behavior?.kappa} />
                  </td>
                </tr>
              </tbody>
            </table>
            <p className="provenance-foot">
              Run <span className="mono">{data.run?.mode}</span> · prompt bundle{" "}
              <span className="mono">{data.run?.prompt_bundle_version}</span> · analyzer{" "}
              <span className="mono">{data.run?.analyzer_version}</span> · judge{" "}
              <span className="mono">{data.run?.judge_triage_pin ?? "unpinned"}</span> ·{" "}
              {data.run?.labels_loaded} human labels from{" "}
              {data.run?.annotators?.length ? data.run.annotators.join(", ") : "nobody yet"}.
            </p>
          </div>

          <div className="block">
            <h3>What these numbers do not say</h3>
            <ul className="limits">
              <li>
                <b>Consistency is not faithfulness.</b> The consistency check asks only
                whether the stated answer follows from the steps shown. It cannot tell you
                whether those steps are the reasoning that actually produced the answer —
                that is a different question, and the faithfulness panel is where it is asked.
              </li>
              <li>
                <b>A soundness verdict is a model&apos;s opinion until it is calibrated.</b>{" "}
                Precision and recall above are what convert it into a measurement. Where they
                read <i>not yet measured</i>, the soundness figures elsewhere on this site are
                uncalibrated and are labelled as such.
              </li>
              <li>
                <b>Kappa is reported on the uniform random sample only.</b> Per-class F1 is
                reported on a pooled set that deliberately over-samples rare classes, and the
                enrichment factor is stated with it — mixing the two would inflate one of them.
              </li>
              <li>
                <b>Some classes may have no instances at all.</b> Where a class does not occur
                in the sample its F1 is reported as not computable rather than as zero. Zero
                would say the classifier is perfectly bad at it, which is a claim made from no
                measurements.
              </li>
              <li>
                <b>Every figure belongs to one model pin and one prompt bundle</b>, both named
                above. Change either and these numbers expire.
              </li>
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
