/**
 * FE-8 — the degraded / cached-only / replay banners.
 *
 * What FE-8 was specified as, and what it is
 * ------------------------------------------
 * C10.4 pairs these banners with **SSE progress**, because the plan assumed a live re-run
 * streaming its stages into the page. ADR-003 deleted the deployment and this ships as a
 * **static export**: every page is pre-rendered at build time and there is no server to
 * stream from. So the SSE half has no consumer and is not built, and M3-1b — the live
 * re-run — is already marked droppable.
 *
 * **The banners are the half that survives, and they were always the valuable half.** Every
 * state below is reachable today from `report_degraded.json`, which is exactly why G1's
 * degraded fixture was specified to carry all five at once: a state the fixtures cannot
 * reach is a state the frontend cannot be built against, and it becomes a Month-3
 * conversation in the month with no slack for conversations.
 *
 * The rule these follow
 * ---------------------
 * **A banner names what is missing and what is still true.** "Something went wrong" makes a
 * reader distrust the whole page; "this arm failed, the other two are unaffected" tells
 * them exactly how much to discount. Every string below does the second thing — which is
 * the same instinct as `trace_quality` having three values instead of two.
 *
 * Per-arm degradation is already rendered inline by `ArmPanes`, `Trace` and `Scoreboard`.
 * This is the **run-level** summary: the thing a reader needs before they start reading,
 * rather than after they have scrolled past it.
 */

function Banner({ tone, title, children }) {
  return (
    <div className={`banner ${tone}`}>
      <b>{title}</b> {children}
    </div>
  );
}

export default function Banners({ report, arms, live = false }) {
  const failed = arms.filter((a) => a.status === "failed");
  const degraded = arms.filter((a) => a.degraded);
  const summarised = arms.filter((a) => a.trace_quality === "provider_summarised");
  const partial = arms.filter((a) => a.trace_quality === "partial" && a.status !== "failed");
  const capped = arms.filter((a) => a.escalation_capped);
  const bound = arms.filter((a) => a.budget_bound);
  const authored = String(report?.versions?.model_pin || "").startsWith("fixture");

  return (
    <>
      {/* Cached-only. The shipping default, and stated as a property rather than an
          apology: C4.9 makes the read path never call a model, and B4 #8's p90 is priced
          on exactly that. */}
      {!live ? (
        <Banner tone="info" title="Served from cache.">
          Every report on this page was computed ahead of time and is read from disk. No
          model runs when you load it — that is the design, not a limitation, and it is what
          makes the numbers on this page reproducible from the pins below them.
        </Banner>
      ) : null}

      {/* FE-11's L3 replay surface. Non-dismissible by construction: it is not a toast. */}
      {authored ? (
        <Banner tone="warn" title="Illustrative fixture, not a measured run.">
          This report was hand-authored to exercise a rendering state the corpus cannot
          currently produce — see the calibration page for which states those are and why.
          Nothing here is evidence about a model.
        </Banner>
      ) : null}

      {failed.length ? (
        <Banner tone="stop" title={`${failed.length} arm${failed.length > 1 ? "s" : ""} failed.`}>
          The provider did not return after its retry, so {failed.length > 1 ? "these arms have" : "this arm has"}{" "}
          no trace and no metrics. <b>The other arms are unaffected</b> and everything they
          show was measured normally.
        </Banner>
      ) : null}

      {degraded.length ? (
        <Banner tone="warn" title="Some steps are unannotated.">
          The classifier could not return a conforming row for every step of{" "}
          {degraded.map((a) => a.strategy).join(", ")}, so that trace renders{" "}
          <b>without labels rather than with guessed ones</b>. The reasoning text is
          complete and unaltered; only the behaviour and soundness columns are missing.
        </Banner>
      ) : null}

      {summarised.length ? (
        <Banner tone="warn" title="One trace is a provider summary, not raw reasoning.">
          {summarised.map((a) => a.strategy).join(", ")} returned a summary of its thinking
          rather than the chain itself. The steps are real text, but they are{" "}
          <b>second-hand</b>, and step counts are not comparable with the raw arms.
        </Banner>
      ) : null}

      {/*
        E12-D4, two of five testers. This banner used to say the run "timed out, or produced
        reasoning and no visible answer" -- a disjunction the reader cannot resolve, on the
        arm the site's headline rests on. One asked the question that matters: truncated by a
        token cap, dropped by the harness, or genuinely emitted and then cut off? THE PAGE'S
        OWN ARGUMENT THAT NOTHING WAS LOST IN THE READING DEPENDED ON AN ANSWER IT NEVER GAVE.

        Worse, the first half of that disjunction CANNOT APPLY HERE. A timed-out arm carries
        status "failed" and is described by the failed-arm banner above; this list filters
        those out. So the banner was offering a cause that is impossible for the arms it was
        describing, which is a good way to make a careful reader distrust the rest.

        The distinction is in the data and is now rendered per arm. `partial` is assigned by
        one rule (runner/run.py): an arm that asked for reasoning and got none, or produced a
        completion with no final-answer line. Neither is truncation, and saying so is the
        point -- "the model never stated an answer" is a RESULT, and "the harness lost it"
        would be a DEFECT, and the whole of mb-08's value rests on which one this is.
      */}
      {partial.length ? (
        <Banner tone="warn" title="One trace is incomplete, and here is how.">
          {partial.map((a, i) => (
            <span key={a.strategy}>
              {i > 0 ? " " : ""}
              <b>{a.strategy}</b> is marked <code>partial</code> because it{" "}
              {!a.final_answer
                ? "produced reasoning and never stated an answer — the steps are all present, and there is no answer in them"
                : "was asked for a reasoning trace and returned none"}
              .{" "}
            </span>
          ))}
          <b>This is not truncation.</b> Nothing was cut short by a token cap and nothing was
          dropped in the capture: the run completed and is recorded as it arrived. A missing
          answer is reported as missing rather than scored as wrong, because a model that
          never answered and a model that answered wrongly are different results.
        </Banner>
      ) : null}

      {capped.length ? (
        <Banner tone="warn" title="The escalation cap bound.">
          More steps qualified for the frontier judge than the per-run cap allows, so the
          lowest-ranked ones carry the <b>first-pass verdict only</b>. They are not
          unchecked; they are less checked, and the flagged-step panel says which.
        </Banner>
      ) : null}

      {bound.length ? (
        <Banner tone="info" title="A thinking budget was reached.">
          {bound.map((a) => a.strategy).join(", ")} reached the token budget this run
          nominated. Cost-of-thought for that arm is therefore a{" "}
          <b>floor, not a measurement</b> — the model may have kept going without it.
        </Banner>
      ) : null}
    </>
  );
}
