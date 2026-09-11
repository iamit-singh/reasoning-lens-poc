import Link from "next/link";
import { allReports, armsOf, reportFor } from "../../lib/reports";
import ArmPanes from "../../components/ArmPanes";
import Provenance from "../../components/Provenance";
import Trace from "../../components/Trace";
import { taxonomy } from "../../lib/taxonomy";

/**
 * The per-item route (FE-1's routing half).
 *
 * `generateStaticParams` is what makes this a static export: every item gets its own HTML
 * file at build time, so the demo works from `file://` with nothing running — the fallback
 * ADR-003 leaves standing when one laptop is the whole deployment.
 */
export function generateStaticParams() {
  return allReports().map((report) => ({ id: report.item.id }));
}

export default async function ItemPage({ params }) {
  const { id } = await params;
  const report = reportFor(id);

  if (!report) {
    return (
      <>
        <p className="notice">No report for {id} in this build.</p>
        <Link className="backlink" href="/">
          ← every item
        </Link>
      </>
    );
  }

  const arms = armsOf(report);

  return (
    <>
      <Link className="backlink" href="/">
        ← every item
      </Link>

      <section className="featured" style={{ marginTop: 14 }}>
        <header>
          <p className="eyebrow mono">{report.item.id}</p>
          <h2 style={{ fontSize: 16, fontWeight: 500, lineHeight: 1.45 }}>
            {report.item.prompt}
          </h2>
          <p className="verdict">
            {report.scoreboard?.verdict_line ?? verdictFallback(report)}
          </p>
        </header>
        <ArmPanes arms={arms} />
      </section>

      <Provenance report={report} />

      <Trace arms={arms} definitions={taxonomy()} />

      {/* FE-3's scoreboard and FE-4's flagged-step panel land below this. Named rather than
          left blank so the next person does not wonder whether something failed to load. */}
      <p className="notice">
        The scoreboard with its verdict line (FE-3) and the flagged-step side panel (FE-4)
        render below this line.
      </p>

      <footer>
        {report.measurement_context &&
        report.measurement_context.classifier_kappa_heldout === null ? (
          <>
            <b>No agreement numbers yet.</b> The calibration run is M2-17; until it happens
            every field in <code>measurement_context</code> is null, and I3 requires that to
            read as <i>not yet measured</i> rather than as a good score.
          </>
        ) : null}
      </footer>
    </>
  );
}

function verdictFallback(report) {
  const ratio = report.scoreboard?.cost_of_thought_ratio;
  if (ratio) return `Extended thinking spent ${ratio}× the reasoning tokens of Direct.`;
  return "Three strategies, one problem.";
}
