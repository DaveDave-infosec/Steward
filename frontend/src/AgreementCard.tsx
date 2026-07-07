import { useState } from "react";
import { acceptAgreement, reserveCapital, getAgreementRaw } from "./lib/contracts";
import { executeReview } from "./lib/review";

function CapitalBar({ reserved, released, withheld, revoked }: { reserved: number; released: number; withheld: number; revoked: number }) {
  const total = reserved + released + withheld + revoked;
  if (total <= 0) return null;
  return (
    <div>
      <div className="capital-bar">
        {reserved > 0 && <div className="seg seg-reserved" style={{ flex: reserved }} title={"reserved " + reserved} />}
        {released > 0 && <div className="seg seg-released" style={{ flex: released }} title={"released " + released} />}
        {withheld > 0 && <div className="seg seg-withheld" style={{ flex: withheld }} title={"withheld " + withheld} />}
        {revoked > 0 && <div className="seg seg-revoked" style={{ flex: revoked }} title={"revoked " + revoked} />}
      </div>
      <div className="capital-legend">
        {reserved > 0 && <span className="legend-item"><span className="legend-swatch sw-reserved" />reserved {reserved}</span>}
        {released > 0 && <span className="legend-item"><span className="legend-swatch sw-released" />released {released}</span>}
        {withheld > 0 && <span className="legend-item"><span className="legend-swatch sw-withheld" />withheld {withheld}</span>}
        {revoked > 0 && <span className="legend-item"><span className="legend-swatch sw-revoked" />revoked {revoked}</span>}
      </div>
    </div>
  );
}

export function AgreementCard({ agreement, address, onChanged, autoBusy, autoKey }: { agreement: any; address: string; onChanged: () => void; autoBusy?: boolean; autoKey?: string | null }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<any>(null);
  const [reviewed, setReviewed] = useState<number[]>([]);

  const a = agreement;
  const me = address.toLowerCase();
  const isCreator = me === a.creator;
  const isRecipient = me === a.recipient;
  const trancheSum = a.checkpoints.reduce((s: number, c: any) => s + c.tranche_amount, 0);
  const revoked = a.status === "cancelled" ? Math.max(0, trancheSum - a.released_total - a.withheld_total - a.reserved) : 0;

  async function run(label: string, expectFrom: string, fn: () => Promise<any>) {
    setBusy(true); setErr(null); setMsg(label);
    try {
      await fn();
      let ag = await getAgreementRaw(a.agreement_id);
      let t = 0;
      while (ag && ag.status === expectFrom && t < 12) {
        await new Promise((r) => setTimeout(r, 2500));
        ag = await getAgreementRaw(a.agreement_id);
        t++;
      }
      setMsg(null);
      await onChanged();
    } catch (e: any) { setErr(e?.message ?? String(e)); setMsg(null); }
    finally { setBusy(false); }
  }

  async function runReviewFlow(c: any) {
    setBusy(true); setErr(null); setVerdict(null);
    try {
      const v = await executeReview(address, a.agreement_id, c.index, c.evidence_url, c.criteria, (m) => setMsg(m));
      setVerdict(v);
      setReviewed((prev) => [...prev, c.index]);
      setMsg(null);
      await onChanged();
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      setMsg(null);
    } finally {
      setBusy(false);
    }
  }

  const canReview = (c: any) =>
    a.status === "active" && c.index === a.current_index && !reviewed.includes(c.index) &&
    (c.status === "pending" || c.status === "paused" || c.status === "escalated");

  return (
    <article className="agreement-row">
      <div className="agr-head">
        <span className="agr-id mono">{a.agreement_id}</span>
        <span className={"status status-" + a.status}>{a.status}</span>
      </div>
      <div className="agr-meta mono">
        <span>allocation {trancheSum}</span>
        <span>reserved {a.reserved}</span>
        <span>checkpoint {a.current_index}/{a.checkpoint_count}</span>
      </div>
      <div className="agr-parties mono">
        <span>creator {a.creator.slice(0, 6)}…{a.creator.slice(-4)}{isCreator ? " (you)" : ""}</span>
        <span>recipient {a.recipient.slice(0, 6)}…{a.recipient.slice(-4)}{isRecipient ? " (you)" : ""}</span>
      </div>

      <CapitalBar reserved={a.reserved} released={a.released_total} withheld={a.withheld_total} revoked={revoked} />

      <div className="cp-list">
        {a.checkpoints.map((c: any) => {
          const disp = (a.status === "cancelled" && c.status === "pending") ? "void" : (reviewed.includes(c.index) && c.status === "pending" ? "resolving" : c.status);
          const thisKey = a.agreement_id + "#" + c.index;
          return (
            <div key={c.index} className={"cp-line cp-" + disp}>
              <div className="cp-line-head">
                <span className="mono cp-num">checkpoint {c.index}</span>
                <span className="mono cp-tranche">{c.tranche_amount} genUSDC</span>
                <span className={"cp-status cp-status-" + disp}>{disp}</span>
              </div>
              <div className="cp-criteria">{c.criteria}</div>
              <a className="cp-url mono" href={c.evidence_url} target="_blank" rel="noreferrer">{c.evidence_url}</a>
              {c.status !== "pending" && (
                <div className="cp-result mono">
                  fulfillment {c.fulfillment_pct}% · released {c.released} · withheld {c.withheld}
                </div>
              )}
              {canReview(c) && (
                autoBusy ? (
                  <button className={"primary review-btn" + (autoKey === thisKey ? " pending" : "")} disabled>
                    {autoKey === thisKey ? "Auto-reviewing…" : "Scheduler will run this"}
                  </button>
                ) : (
                  <button className={"primary review-btn" + (busy ? " pending" : "")} disabled={busy} onClick={() => runReviewFlow(c)}>
                    {busy ? "Reviewing…" : "Run Review"}
                  </button>
                )
              )}
            </div>
          );
        })}
      </div>

      <div className="agr-actions">
        {a.status === "locked" && isRecipient && (
          <button className={busy ? "pending" : ""} disabled={busy} onClick={() => run("Accepting…", "locked", () => acceptAgreement(address, a.agreement_id))}>
            {busy ? "Accepting…" : "Accept agreement"}
          </button>
        )}
        {a.status === "accepted" && isCreator && (
          <button className={"primary" + (busy ? " pending" : "")} disabled={busy} onClick={() => run("Reserving…", "accepted", () => reserveCapital(address, a.agreement_id, trancheSum))}>
            {busy ? "Reserving…" : "Reserve " + trancheSum + " genUSDC"}
          </button>
        )}
        {a.status === "locked" && !isRecipient && <span className="waiting-hint">Awaiting recipient acceptance…</span>}
        {a.status === "accepted" && !isCreator && <span className="waiting-hint">Awaiting the creator to reserve capital…</span>}
        {a.status === "active" && !isCreator && <span className="waiting-hint">Awaiting checkpoint reviews by the creator…</span>}
      </div>

      {msg && <div className="status-line mono live-status">⋯ {msg}</div>}
      {verdict && (
        <div className="verdict-box">
          <div className="verdict-head mono">VERDICT · {verdict.outcome} · {Number(verdict.fulfillment_pct)}%</div>
          <div className="verdict-reasoning">{verdict.reasoning}</div>
          {verdict.minority_note && <div className="verdict-minority">Minority note: {verdict.minority_note}</div>}
        </div>
      )}
      {err && <div className="error mono">{err}</div>}
    </article>
  );
}
