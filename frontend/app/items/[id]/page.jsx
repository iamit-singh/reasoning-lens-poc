import Link from "next/link";
import {
  allReports,
  armsOf,
  liveLatency,
  reportFor,
  replayEntries,
  replayFor,
} from "../../lib/reports";
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

// E12-D2/D3. Read from the artifact, never typed: a hash typed into a page is a second copy
// of a fact that can drift from the file it claims to describe -- the mistake FE-11 already
// made once with C1.3's thresholds, and the mistake that produced this defect in the first
// place.
const PLANTED_BUNDLE_FALLBACK = "an earlier bundle";

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
          Everything else in the trace is the model&rsquo;s own work.{" "}
          {/*
            E12-D2 / E12-D3, two of five testers, found independently. These pages render a
            DIFFERENT PROMPT BUNDLE from the measured pages, and their judge field renders as
            a bare em-dash because these reports carry no `versions` block at all. A reader
            who noticed got no way to tell a deliberate distinction from undetected drift --
            one spent their only recorded confusion on exactly that question and still did
            not know at the end. Their own suggestion, adopted here verbatim: "a single line
            on the planted-error banner -- these traces were judged under bundle X on date Y
            -- would settle it and would cost nothing."

            IT IS DRIFT, AND SAYING SO IS THE HONEST OPTION. The alternative -- writing in a
            judge pin we infer from M2-6's raw records rather than one this artifact captured
            -- would be fabricating provenance on the one surface whose whole job is to show
            it. The measurements are unaffected: M2-6's evidence IS at the shipping bundle,
            so judge recall 0.80 is correctly attributed. `make bundle-check` now fails the
            build if this vintage stops being declared.
          */}
          <span className="vintage">
            <b>Provenance, stated because this page cannot show it:</b> these traces were
            judged under prompt bundle{" "}
            {replay.prompt_bundle_version ? (
              <code>{replay.prompt_bundle_version}</code>
            ) : (
              PLANTED_BUNDLE_FALLBACK
            )}
            , an earlier one than the
            measured pages, and this report predates the run that captures the judge pin —
            which is why the judge reads &ldquo;—&rdquo; above rather than naming a model.
            Re-judging them would be a new measurement of the instrument, not a rebuild, so
            they ship labelled rather than quietly refreshed.
          </span>
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
      {replay ? null : (
        <LiveRun itemId={report.item.id} latency={liveLatency(report.item.id)} />
      )}

      <footer>
        {report.measurement_context &&
        report.measurement_context.classifier_kappa_heldout === null ? (
          <>
            {/* Was "No agreement numbers yet. The calibration run is M2-17; until it
                happens..." -- true in W5, false since 16 Sep, and still rendering on every
                seeded-error page at the 28 Sep close-out: E12-D1's contradiction on the
                pages the stamp does not reach. */}
            <b>This report is outside the published calibration.</b> The agreement figures
            on <a href="/calibration/">/calibration/</a> qualify the reports they were
            stamped into; every field of <code>measurement_context</code> here is null, and
            I3 requires that to read as <i>not calibrated</i> rather than as a good score.
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
