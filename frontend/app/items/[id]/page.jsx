import Link from "next/link";
import { allReports, armsOf, reportFor, replayEntries, replayFor } from "../../lib/reports";
import ArmPanes from "../../components/ArmPanes";
import Provenance from "../../components/Provenance";
import Trace from "../../components/Trace";
import Scoreboard from "../../components/Scoreboard";
import FlaggedPanel from "../../components/FlaggedPanel";
import Download from "../../components/Download";
import LiveRun from "../../components/LiveRun";
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
  return [
    ...allReports().map((report) => ({ id: report.item.id })),
    // FE-11 / L3: the seeded-error replays are **labeled bank entries**, not a separate UI
    // mode, so they get ordinary item routes keyed by case id. Pre-rendered like everything
    // else, which is what makes this the surface that still works during a provider outage.
    ...replayEntries().map((entry) => ({ id: entry.case_id })),
  ];
}

export default async function ItemPage({ params }) {
  const { id } = await params;
  // A replay id (`SE-01`) never collides with a bank id (`mb-*`) or a fixture id (`fx-*`).
  // The entry is the wrapper; `entry.report` is the untouched `ReasoningReport`, which is
  // what every component below — including the download — receives.
  const replay = replayFor(id);
  const report = replay ? replay.report : reportFor(id);

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

      {/* FE-11 / L3. **Non-dismissible, and first.** A planted error presented without its
          label is the one thing on this site that would be actively misleading, so this
          cannot be a toast, cannot be closed, and sits above everything a reader would take
          as a finding. It is plain markup with no handler — there is nothing to dismiss. */}
      {replay ? (
        <div className="notice planted" role="note">
          <b>Illustrative: an error was deliberately planted in this trace.</b> This is not a
          measured failure. The step{" "}
          <code>{replay.mutated_step_id}</code> was edited by hand before the judge saw it —
          mutation type <code>{replay.mutation_type.replace(/_/g, " ")}</code> — to show what
          the instrument does when something is wrong.{" "}
          {replay.judge_flagged_the_mutated_step ? (
            <>The judge <b>caught it</b>.</>
          ) : (
            <>
              The judge <b>missed it</b>, and that is shown rather than hidden.
            </>
          )}{" "}
          Everything else in the trace is the model&rsquo;s own work.
        </div>
      ) : null}

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

      {/* E2. Renders nothing unless the backend reports `live_runs: true`, so the static
          export and the cached demo are untouched. A replay entry is a deliberately
          mutated trace, so re-running it live would produce a clean report under a
          planted-error id -- the one combination that would be actively misleading. */}
      {replay ? null : <LiveRun itemId={report.item.id} />}

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
