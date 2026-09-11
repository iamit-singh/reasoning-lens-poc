import { isAuthored } from "../lib/reports";

/**
 * Says where the numbers on this page came from.
 *
 * **This is not a debug affordance.** Three of the four committed fixtures are hand-authored
 * — the escalation tier and the consistency checker do not exist until Month 2, so a flagged
 * step and a degraded run cannot occur naturally yet. A page that rendered an authored
 * fixture identically to a measured report would be showing a reviewer invented numbers
 * inside a real-looking provenance block, which is the most damaging thing this frontend
 * could do. So it is loud, and it is on every page that shows a number.
 */
export default function Provenance({ report }) {
  const authored = isAuthored(report);
  const v = report.versions;
  return (
    <div className={authored ? "provenance" : "provenance measured"}>
      {authored ? (
        <span>
          <b>Illustrative fixture — these numbers were authored, not measured.</b> It exists so
          this surface can be built against states the pipeline cannot produce yet.
        </span>
      ) : (
        <span>
          <b>Measured run.</b> Generated {report.generated_at}.
        </span>
      )}
      <span className="mono" style={{ marginLeft: "auto", fontSize: "11.5px" }}>
        model {v.model_pin_fields?.model ?? "—"} · pin {v.model_pin.slice(0, 10)} · judge{" "}
        {v.judge_triage_pin ?? "—"} · prompts {v.prompts.slice(0, 10)}
      </span>
    </div>
  );
}
