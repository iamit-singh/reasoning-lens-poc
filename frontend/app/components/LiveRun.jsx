"use client";

import { useEffect, useRef, useState } from "react";

/**
 * E2's progress surface — the SSE half, rebuilt against the backend that actually exists.
 *
 * C10.4 budgeted this against a hosted service; ADR-003 deleted the hosting and the whole
 * feature went with it. What survived the deletion is a backend that runs on a laptop and
 * serves this page from the same origin (FE-9), so `fetch("/api/…")` and `EventSource` work
 * with no CORS, no host and no configuration.
 *
 * **It renders nothing unless the backend says live runs are on**, and that is the important
 * property rather than a nicety. The shipping demo is a static export opened from `file://`
 * or served with `DEMO_MODE=cached`, where there is no API at all — and a control that
 * offers to re-run a model and then fails is worse than no control, because the reader
 * cannot tell whether the demo is broken or the feature is off. So the probe runs first and
 * the button only exists once the answer is yes.
 *
 * **Nothing here is on the pre-rendered path.** `make fe-export-check` strips every
 * `<script>` and asserts the page still reads; this component contributes no text to that
 * view by design, so the static export's guarantee is untouched.
 */
/**
 * How long a re-run takes, from B4 #8's live measurement -- never a typed guess. The old
 * copy said "about a minute", which is the median and was off by four on the featured item.
 * States this item's own measured time when there is one, and the bank's median and worst
 * case beside it, with n, because one run per item is one observation.
 */
function Duration({ latency }) {
  if (!latency) return null;
  const { itemSeconds, p50, max, n, measured } = latency;
  const mins = (s) => (s >= 90 ? `${(s / 60).toFixed(1)} min` : `${Math.round(s)} s`);
  return (
    <>
      {itemSeconds !== null ? (
        <>
          Measured on {measured}, this item took <b>{mins(itemSeconds)}</b>
        </>
      ) : (
        <>Measured on {measured}</>
      )}
      ; across the bank the median was {mins(p50)} and the slowest {mins(max)} (n = {n}, one
      run each, one machine, model already loaded).
    </>
  );
}

export default function LiveRun({ itemId, latency }) {
  const [available, setAvailable] = useState(null); // null = still asking
  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [stages, setStages] = useState([]);
  const [done, setDone] = useState(null);
  const [error, setError] = useState(null);
  const source = useRef(null);

  useEffect(() => {
    let cancelled = false;
    // A short timeout rather than an open-ended fetch: on `file://` this request does not
    // fail fast, and an unresolved probe would leave the section in "still asking" forever.
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 2000);
    fetch("/readyz", { signal: abort.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => !cancelled && setAvailable(Boolean(d && d.live_runs)))
      .catch(() => !cancelled && setAvailable(false))
      .finally(() => clearTimeout(timer));
    return () => {
      cancelled = true;
      abort.abort();
      if (source.current) source.current.close();
    };
  }, []);

  function start() {
    setEvents([]);
    setDone(null);
    setError(null);
    fetch("/api/runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ item_id: itemId }),
    })
      .then(async (r) => {
        const body = await r.json();
        if (!r.ok) throw new Error(body.detail || `HTTP ${r.status}`);
        return body;
      })
      .then((body) => {
        setRun(body);
        setStages(body.stages || []);
        const es = new EventSource(body.events_url);
        source.current = es;
        es.addEventListener("progress", (e) => {
          setEvents((prev) => [...prev, JSON.parse(e.data)]);
        });
        es.addEventListener("end", (e) => {
          setDone(JSON.parse(e.data));
          es.close();
        });
        // A transport error is not a run failure and must not be reported as one: the run
        // may well have finished. The status route is the authority, so say what is known.
        es.onerror = () => {
          es.close();
          setDone((d) => d ?? { status: "unknown", transport: true });
        };
      })
      .catch((e) => setError(String(e.message || e)));
  }

  if (available !== true) return null;

  const reached = new Set(events.map((e) => e.stage));
  const running = run && !done;

  return (
    <section className="liverun">
      <h2>Re-run this item live</h2>
      <p className="hint">
        Generates all three arms again on the local model, then classifies them, and spends
        real analysis calls. <Duration latency={latency} />{" "}
        <strong>The result is not a published measurement</strong> — the numbers on this page
        are the cached run everyone else sees.
      </p>

      {!run ? (
        <button className="tag" onClick={start}>
          Re-run {itemId}
        </button>
      ) : null}

      {error ? <p className="notice">Could not start a run: {error}</p> : null}

      {run ? (
        <>
          {/* The whole ladder up front, not a list that grows. A reader who can see what is
              still to come can tell "slow" from "stuck"; one who cannot is watching a
              spinner with extra steps. */}
          <ol className="ladder">
            {stages.map((s) => {
              const mine = events.filter((e) => e.stage === s);
              const bad = mine.find((e) => e.status === "failed");
              const soft = mine.find((e) => e.status === "degraded");
              const state = bad ? "failed" : soft ? "degraded" : reached.has(s) ? "ok" : "todo";
              return (
                <li key={s} className={`rung ${state}`}>
                  <span className="name">{s}</span>
                  <span className="detail">
                    {mine.length ? mine[mine.length - 1].detail : state === "todo" ? "…" : ""}
                  </span>
                </li>
              );
            })}
          </ol>

          {/* Degraded events are surfaced in full rather than folded into the rung, because
              "which arm degraded and why" is the content, not the fact that one did. */}
          {events.filter((e) => e.status === "degraded" || e.status === "failed").length ? (
            <ul className="degradedlist">
              {events
                .filter((e) => e.status === "degraded" || e.status === "failed")
                .map((e) => (
                  <li key={e.seq} className={e.status}>
                    <strong>{e.status}</strong> — {e.detail}
                  </li>
                ))}
            </ul>
          ) : null}

          {running ? <p className="hint">Running…</p> : null}

          {done ? (
            <div className={`runend ${done.status}`}>
              <strong>
                {done.status === "done"
                  ? "Finished"
                  : done.status === "unknown"
                    ? "Stream dropped"
                    : "Failed"}
              </strong>
              {done.error ? <> — {done.error}</> : null}
              {done.transport ? (
                <> — the connection closed; check the run status for the real outcome.</>
              ) : null}
              {done.tokens ? (
                <p className="hint">
                  {done.analysis_calls} analysis calls · {done.tokens.reasoning} reasoning
                  tokens measured.{" "}
                  <strong>Cost is not shown because it is not priced</strong> — the rate
                  table is deliberately empty, so a dollar figure here would be an estimate
                  wearing a measurement&rsquo;s clothes.
                </p>
              ) : null}
              {done.status === "done" ? (
                <p className="hint">
                  <a href={`/api/runs/${run.run_id}/report`}>Open the report this run built →</a>{" "}
                  It is flagged <code>live: true</code> and carries no{" "}
                  <code>measurement_context</code>: one unrepeated run, not the published
                  number.
                </p>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
