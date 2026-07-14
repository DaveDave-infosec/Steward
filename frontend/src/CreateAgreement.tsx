import { useState } from "react";
import { createAgreement, addCheckpoint, finalizeAgreement, getAgreementCount } from "./lib/contracts";

type CheckpointDraft = {
  evidenceUrl: string;
  criteria: string;
  trancheAmount: string;
  reviewCadence: string;
};

const emptyCheckpoint = (): CheckpointDraft => ({
  evidenceUrl: "",
  criteria: "",
  trancheAmount: "",
  reviewCadence: "manual",
});

export function CreateAgreement({ account, onCreated }: { account: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [maxAllocation, setMaxAllocation] = useState("");
  const [checkpoints, setCheckpoints] = useState<CheckpointDraft[]>([emptyCheckpoint()]);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateCp(i: number, patch: Partial<CheckpointDraft>) {
    setCheckpoints((cs) => cs.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  }
  function addCp() { setCheckpoints((cs) => [...cs, emptyCheckpoint()]); }
  function removeCp(i: number) { setCheckpoints((cs) => cs.filter((_, idx) => idx !== i)); }

  function loadSample() {
    setError(null);
    setRecipient(account);
    setMaxAllocation("1000");
    setCheckpoints([
      {
        evidenceUrl: "https://api.github.com/repos/DaveDave-infosec/Balance/contents/contracts",
        criteria: "The contracts directory contains the Balance Intelligent Contract as a Python source file (balance).",
        trancheAmount: "500",
        reviewCadence: "manual",
      },
      {
        evidenceUrl: "https://raw.githubusercontent.com/DaveDave-infosec/Balance/main/README.md",
        criteria: "The project both (a) documents a deployed Intelligent Contract performing proportional, consensus-based escrow settlement, and (b) has published a tagged v1.0.0 release.",
        trancheAmount: "500",
        reviewCadence: "manual",
      },
    ]);
  }

  const trancheTotal = checkpoints.reduce((s, c) => s + (Number(c.trancheAmount) || 0), 0);

  function validate(): string | null {
    if (!recipient.startsWith("0x") || recipient.length !== 42) return "Recipient must be a valid 0x address.";
    if (!(Number(maxAllocation) > 0)) return "Max allocation must be a positive number.";
    if (checkpoints.length === 0) return "Add at least one checkpoint.";
    for (const c of checkpoints) {
      if (!c.evidenceUrl.startsWith("http://") && !c.evidenceUrl.startsWith("https://")) return "Each checkpoint needs a full evidence URL starting with http:// or https://";
      if (c.criteria.trim().length < 4) return "Each checkpoint needs verification criteria.";
      if (!(Number(c.trancheAmount) > 0)) return "Each tranche amount must be positive.";
    }
    if (trancheTotal > Number(maxAllocation)) return "Tranche total exceeds max allocation.";
    return null;
  }

  async function submit() {
    const v = validate();
    if (v) { setError(v); return; }
    setError(null);
    setBusy(true);
    try {
      const count = await getAgreementCount();
      const agreementId = "agr_" + count;
      setStatus("Creating agreement…");
      await createAgreement(account, recipient, Number(maxAllocation));
      for (let i = 0; i < checkpoints.length; i++) {
        const c = checkpoints[i];
        setStatus("Locking checkpoint " + (i + 1) + " of " + checkpoints.length + "…");
        await addCheckpoint(account, agreementId, c.evidenceUrl, c.criteria, Number(c.trancheAmount), c.reviewCadence);
      }
      setStatus("Finalizing — locking criteria & sources immutably…");
      await finalizeAgreement(account, agreementId);
      setRecipient(""); setMaxAllocation(""); setCheckpoints([emptyCheckpoint()]);
      setStatus(null);
      setOpen(false);
      await onCreated();
    } catch (e: any) {
      setError(e?.message ?? String(e));
      setStatus(null);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return <button className="new-order-btn" onClick={() => setOpen(true)}>+ New Standing Order</button>;
  }

  return (
    <div className="create-panel">
      <div className="create-head">
        <h3>New Standing Order</h3>
        <div className="create-head-actions">
          <button className="link" type="button" onClick={loadSample} disabled={busy}>load sample grant</button>
          <button className="link" type="button" onClick={() => setOpen(false)}>close</button>
        </div>
      </div>

      <label className="field">
        <span>Recipient address <button className="link" type="button" onClick={() => setRecipient(account)}>use my address</button></span>
        <input className="mono" value={recipient} onChange={(e) => setRecipient(e.target.value)} placeholder="0x…" />
      </label>
      <label className="field">
        <span>Max allocation (genUSDC)</span>
        <input className="mono" value={maxAllocation} onChange={(e) => setMaxAllocation(e.target.value)} placeholder="1000" />
      </label>

      <div className="cp-builder">
        <div className="cp-builder-head">
          <span className="section-title">Verification Checkpoints</span>
          <span className="mono muted">tranche total {trancheTotal}</span>
        </div>
        {checkpoints.map((c, i) => (
          <div className="cp-draft" key={i}>
            <div className="cp-draft-head">
              <span className="mono cp-num">checkpoint {i}</span>
              {checkpoints.length > 1 && <button className="link" type="button" onClick={() => removeCp(i)} disabled={busy}>remove</button>}
            </div>
            <label className="field">
              <span>Locked evidence source (URL)</span>
              <input className="mono" value={c.evidenceUrl} onChange={(e) => updateCp(i, { evidenceUrl: e.target.value })} placeholder="https://api.github.com/repos/owner/repo/tags" />
            </label>
            <label className="field">
              <span>Locked verification criteria</span>
              <textarea value={c.criteria} onChange={(e) => updateCp(i, { criteria: e.target.value })} placeholder="Repository has published tag v1.0.0 implementing the indexer" rows={2} />
            </label>
            <div className="cp-row">
              <label className="field small">
                <span>Tranche</span>
                <input className="mono" value={c.trancheAmount} onChange={(e) => updateCp(i, { trancheAmount: e.target.value })} placeholder="600" />
              </label>
              <label className="field small">
                <span>Review cadence</span>
                <input className="mono" value={c.reviewCadence} onChange={(e) => updateCp(i, { reviewCadence: e.target.value })} placeholder="manual" />
              </label>
            </div>
          </div>
        ))}
        <button className="link" type="button" onClick={addCp} disabled={busy}>+ add checkpoint</button>
      </div>

      {error && <div className="error mono">{error}</div>}
      {status && <div className="status-line mono live-status">⋯ {status}</div>}

      <button className="primary submit" onClick={submit} disabled={busy}>
        {busy ? "Processing… please wait" : "Create & lock agreement"}
      </button>
    </div>
  );
}
