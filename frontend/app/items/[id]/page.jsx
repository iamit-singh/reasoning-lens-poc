import Link from "next/link";
import { allReports, armsOf, reportFor } from "../../lib/reports";
import ArmPanes from "../../components/ArmPanes";
import Provenance from "../../components/Provenance";
import Trace from "../../components/Trace";
import Scoreboard from "../../components/Scoreboard";
import FlaggedPanel from "../../components/FlaggedPanel";
import Download from "../../components/Download";
import Banners from "../../components/Banners";
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

      {/* FE-8. Run-level, and ABOVE the report: a reader needs to know how much to
          discount before they read, not after they have scrolled past it. */}
      <Banners report={report} arms={arms} />

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

      <Scoreboard report={report} arms={arms} />

      <Trace arms={arms} definitions={taxonomy()} />

      <FlaggedPanel arms={arms} />

      <Download report={report} />

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
