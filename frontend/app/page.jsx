import {
  allReports,
  armsOf,
  featured,
  isAuthored,
  replayEntries,
  startHere,
  tagIndex,
  ARM_LABEL,
} from "./lib/reports";
import { calibration } from "./lib/calibration";
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
          {effortNote(arms)}
          <p className="prompt">
            <span className="mono">{report.item.id}</span> — {report.item.prompt}
          </p>
        </header>
        <ArmPanes arms={arms} />
      </section>

      <Provenance report={report} />

      <StartHere
        entries={startHere(report.item.id)}
        judgePrecision={calibration()?.measurement_context?.judge_precision?.value ?? null}
      />

      <ItemPicker
        tags={tagIndex()}
        items={[
          ...reports.map((r) => ({
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
          })),
          // FE-11 / L3: replay entries sit in the picker as ordinary rows, LAST, and
          // carry `planted` so the chip says what they are. They are listed after the real
          // corpus for the same reason authored fixtures are -- a reviewer should meet the
          // measured work first, not three illustrations of it.
          ...replayEntries().map((e) => ({
            id: e.case_id,
            prompt: e.report.item.prompt,
            tags: e.report.item.tags ?? [],
            planted: true,
            arms: armsOf(e.report).map((a) => ({
              strategy: a.strategy,
              label: ARM_LABEL[a.strategy] ?? a.strategy,
              correct: a.correct,
              degraded: Boolean(a.degraded),
              failed: a.status === "failed",
            })),
          })),
        ]}
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

/**
 * Two doors instead of a directory (E12 queue #4) — see `startHere()` for how they are picked.
 *
 * Renders nothing when the corpus offers nothing to recommend, rather than shipping an empty
 * heading: on a bank with no disagreement and no flagged step there is no honest shortcut to
 * offer, and inventing one would be the page asserting interest it cannot show.
 */
function StartHere({ entries, judgePrecision }) {
  if (!entries.length) return null;
  // E9's rule, applied to this page rather than only to the calibration page: the figure is
  // READ from the same `measurement_context` the calibration page renders, never typed here.
  // A percentage typed into JSX is a second copy of a measurement that goes stale silently —
  // FE-11 already made exactly this mistake once with C1.3's branch thresholds. When the
  // figure is absent the caveat still ships, without a number: the instruction ("a prompt to
  // look") is what the reader needs, and it does not depend on the value.
  const pct =
    typeof judgePrecision === "number" ? `${Math.round(judgePrecision * 100)}% of the time` : null;
  return (
    <section className="starthere">
      <h2>Start with one of these</h2>
      <p className="hint">
        The whole bank is below. These two are where the arms actually come apart.
      </p>
      <div className="doors">
        {entries.map((e) => (
          <a key={e.id} className="door" href={`/items/${e.id}/`}>
            <div className="id mono">{e.id}</div>
            <div className="q">{e.prompt}</div>
            <div className="why">{e.reason}</div>
            {e.caveat ? (
              <div className="caveat">
                The judge that flagged it is right {pct ?? "less often than you would want"} —
                a prompt to look, not a finding.
              </div>
            ) : null}
          </a>
        ))}
      </div>
    </section>
  );
}

/**
 * The second reading the featured block offers (E12 queue #2).
 *
 * The featured contrast is chosen by `featured()` for the most striking *measured* finding,
 * and on this corpus that is the tool contrast — a clear, well-written argument about **tool
 * access**. The heuristic walkthrough review's most consequential finding is that a tester
 * asked *"what is this page telling you about how this AI reasons?"* and answering *"it does
 * better when it can look things up"* has read the page correctly and missed B4 #9 entirely,
 * because the page offers no other reading.
 *
 * This adds the second reading **alongside** the tool story rather than instead of it — the
 * tool contrast is a genuine measured result and the cleanest one in the corpus.
 *
 * **Derived, and silent when the corpus does not support it.** It renders only when the arm
 * that spent the most reasoning is *not* an arm that got the answer right, which is a fact
 * about the three arms in front of the reader and not a thesis typed into a page. If the
 * featured item ever changes to one where the hardest-reasoning arm also wins, this line
 * disappears rather than becoming false — the same rule FE-11's gate block follows, and the
 * same reason E9 forbids a number in the markup.
 */
function effortNote(arms) {
  const scored = arms.filter((a) => a.status !== "failed" && a.metrics?.reasoning_tokens);
  if (scored.length < 2) return null;
  const hardest = scored.reduce((a, b) =>
    b.metrics.reasoning_tokens > a.metrics.reasoning_tokens ? b : a
  );
  if (hardest.correct === true) return null;
  const cheapest = scored.reduce((a, b) =>
    b.metrics.reasoning_tokens < a.metrics.reasoning_tokens ? b : a
  );
  if (cheapest.metrics.reasoning_tokens >= hardest.metrics.reasoning_tokens) return null;
  const ratio = Math.round(hardest.metrics.reasoning_tokens / cheapest.metrics.reasoning_tokens);

  return (
    <p className="verdict effort">
      And a second thing worth looking at, on the same row:{" "}
      <strong>the arm that reasoned hardest is not the arm that got it right.</strong>{" "}
      {ARM_LABEL[hardest.strategy] ?? hardest.strategy} spent{" "}
      {hardest.metrics.reasoning_tokens.toLocaleString()} reasoning tokens over{" "}
      {hardest.steps.length.toLocaleString()} steps
      {ratio > 1 ? <> — about {ratio}× the cheapest arm here — </> : " "}
      and {hardest.correct === false ? "got it wrong" : "never stated an answer"}. How much a
      model reasons and how well it reasons are separate measurements, and this instrument
      reports them separately.
    </p>
  );
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
