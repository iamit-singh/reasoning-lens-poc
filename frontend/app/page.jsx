import { allReports, armsOf, featured, isAuthored, tagIndex, ARM_LABEL } from "./lib/reports";
import ArmPanes from "./components/ArmPanes";
import Provenance from "./components/Provenance";
import ItemPicker from "./components/ItemPicker";

/**
 * FE-1 — the shell, the featured comparison, and the picker.
 *
 * Everything on this page is **pre-rendered at build time** (C11.3). The featured comparison
 * is in the HTML before a browser asks for anything, which is how B4 #8's cached-path budget
 * is met: not by being fast, but by there being nothing to wait for.
 */
export default function Home() {
  const reports = allReports();
  const lead = featured();

  if (!lead) {
    return (
      <p className="notice">
        No reports available to this build. Run <code>make spans</code> then{" "}
        <code>make report ARGS=--all</code>, or check that the fixtures in{" "}
        <code>analyzer/tests/fixtures/reports/</code> are present.
      </p>
    );
  }

  const { report, kind, ratio, rescued } = lead;
  const arms = armsOf(report);

  return (
    <>
      <section className="featured">
        <header>
          <p className="eyebrow">
            {kind === "tool"
              ? "Featured — the tool contrast"
              : kind === "accuracy"
                ? "Featured — the arms disagree"
                : kind === "cost"
                  ? "Featured — the cost of thought"
                  : "Featured"}
          </p>
          <h2>{headline(kind, ratio, rescued, report)}</h2>
          {/* The plan's featured slot was a TRAP comparison. ADR-005 withdrew the category
              after 0 of 16 candidates reproduced, and ADR-006 found the arms do not separate
              on accuracy either. What survived measurement leads instead. */}
          <p className="verdict">{subhead(kind)}</p>
          <p className="prompt">
            <span className="mono">{report.item.id}</span> — {report.item.prompt}
          </p>
        </header>
        <ArmPanes arms={arms} />
      </section>

      <Provenance report={report} />

      <ItemPicker
        tags={tagIndex()}
        items={reports.map((r) => ({
          id: r.item.id,
          prompt: r.item.prompt,
          tags: r.item.tags ?? [],
          authored: isAuthored(r),
          arms: armsOf(r).map((a) => ({
            strategy: a.strategy,
            label: ARM_LABEL[a.strategy] ?? a.strategy,
            correct: a.correct,
            degraded: Boolean(a.degraded),
            failed: a.status === "failed",
          })),
        }))}
      />

      <footer>
        Built against committed fixtures (C4.10). Every number renders beside its provenance;
        none of them is hard-coded in this page.
      </footer>
    </>
  );
}

function headline(kind, ratio, rescued, report) {
  if ((kind === "tool" || kind === "accuracy") && rescued) {
    return `${ARM_LABEL[rescued.correct.strategy]} answered it. ${ARM_LABEL[rescued.wrong.strategy]} did not.`;
  }
  if (kind === "cost" && ratio) {
    return `Extended thinking spent ${ratio}× the reasoning tokens — for the same answer.`;
  }
  return report.item.prompt.slice(0, 80);
}

function subhead(kind) {
  if (kind === "tool") {
    return "Same model, same problem, three strategies. One of them looked the fact up; the others tried to recall it. The lens shows which, and what it cost.";
  }
  if (kind === "accuracy") {
    // Deliberately does NOT say the tool arm rescued it — on this row it did not, and
    // ADR-006 is about exactly this kind of overclaim.
    return "Same model, same problem, three strategies — and they do not agree. The lens shows which step the disagreement starts at, and what each arm spent getting there.";
  }
  if (kind === "cost") {
    return "Same model, same problem, same answer — at very different prices. Cost of thought is the contrast this bank actually produces; the accuracy gap the plan expected is not there, and that is a measured finding rather than a missing feature.";
  }
  return "Same model, same problem, three strategies.";
}
