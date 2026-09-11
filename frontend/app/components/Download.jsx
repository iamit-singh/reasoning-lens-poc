"use client";

/**
 * FE-7 — download the report, and the CTA that replaces a free-text box.
 *
 * **The download is the `ReasoningReport` itself, unmodified.** Not a summary, not a CSV:
 * the same object the page rendered, the same object the schema validates, the same object
 * a golden test runs against. That is what makes "here is what we measured, check it
 * yourself" a real offer rather than a gesture — and it is why the blob is built from the
 * report prop rather than re-serialised from component state.
 *
 * **The CTA is a mailto, not a text input, and that is a security decision.** C4.9 replaces
 * free-text entry with "request a custom run": an input box on a public demo that reaches a
 * model is an open prompt endpoint with somebody else's key behind it, and no amount of
 * rate limiting makes that a thing to leave running unattended.
 */
export default function Download({ report }) {
  function save() {
    const body = JSON.stringify(report, null, 2);
    const url = URL.createObjectURL(new Blob([body], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.item.id}.report.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Revoked on the next tick rather than immediately: Safari has been known to cancel a
    // download whose object URL is released in the same frame as the click.
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  const subject = encodeURIComponent(`Reasoning Lens — a run on my own problem`);
  const body = encodeURIComponent(
    "I would like to see these three arms run on a problem of my own.\n\n" +
      "The problem:\n\n\n" +
      "The answer I expect:\n\n"
  );

  return (
    <div className="actions">
      <button className="action primary" onClick={save}>
        Download this report (JSON)
      </button>
      <a className="action" href={`mailto:?subject=${subject}&body=${body}`}>
        Request a run on your own problem
      </a>
      <p className="note">
        The download is the complete report this page rendered — every step, every label,
        every version pin — not a summary of it. It validates against the committed JSON
        Schema, so anything here can be checked against the same contract the pipeline uses.
      </p>
    </div>
  );
}
