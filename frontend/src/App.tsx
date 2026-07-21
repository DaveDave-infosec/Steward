import { useState, useEffect, useCallback, useRef } from "react";
import { useWallet } from "./lib/useWallet";
import { getAllAgreementIds, getAgreementsFor, getAgreementFull, balanceOf, mint } from "./lib/contracts";
import { executeReview } from "./lib/review";
import { CreateAgreement } from "./CreateAgreement";
import { AgreementCard } from "./AgreementCard";
import { Copyable } from "./Copyable";
import { HowItWorks } from "./HowItWorks";
import { Guide } from "./Guide";
import { Landing } from "./Landing";

function n(x: any): number {
  return Number(x);
}

async function pool<T, R>(items: T[], limit: number, fn: (x: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const cur = i++;
      results[cur] = await fn(items[cur]);
    }
  }
  const count = Math.min(limit, items.length) || 0;
  await Promise.all(Array.from({ length: count }, () => worker()));
  return results;
}

export default function App() {
  const { address, mode, connectMetaMask, useDemo, newDemoWallet, disconnect } = useWallet();
  const [balance, setBalance] = useState<number | null>(null);
  const [agreements, setAgreements] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [minting, setMinting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [view, setView] = useState<"home" | "ledger" | "how" | "guide">("home");
  const [schedulerOn, setSchedulerOn] = useState(false);
  const [schedulerLog, setSchedulerLog] = useState<string[]>([]);
  const [autoKey, setAutoKey] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!address) return;
    setLoading(true);
    setError(null);
    try {
      setBalance(await balanceOf(address));
      const ids = showAll ? await getAllAgreementIds() : await getAgreementsFor(address);
      const loaded = await pool(ids, 4, async (id) => {
        const a = await getAgreementFull(id);
        if (!a || !a.agreement_id) return null;
        let cps: any[] = [];
        try {
          cps = JSON.parse(a.checkpoints_json || "[]");
        } catch {
          cps = [];
        }
        return {
          agreement_id: a.agreement_id,
          creator: (a.creator || "").toLowerCase(),
          recipient: (a.recipient || "").toLowerCase(),
          status: a.status,
          max_allocation: n(a.max_allocation),
          reserved: n(a.reserved),
          released_total: n(a.released_total),
          withheld_total: n(a.withheld_total),
          checkpoint_count: n(a.checkpoint_count),
          current_index: n(a.current_index),
          checkpoints: cps.map((c: any) => ({
            index: n(c.index),
            evidence_url: c.evidence_url,
            criteria: c.criteria,
            tranche_amount: n(c.tranche_amount),
            status: c.status,
            fulfillment_pct: n(c.fulfillment_pct),
            released: n(c.released),
            withheld: n(c.withheld),
            case_id: c.case_id,
          })),
        };
      });
      setAgreements(loaded.filter(Boolean) as any[]);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }, [address, showAll]);

  useEffect(() => {
    if (address) {
      refresh();
    } else {
      setAgreements([]);
      setBalance(null);
    }
  }, [address, refresh]);

  const runningRef = useRef(false);
  const agreementsRef = useRef<any[]>([]);
  const addressRef = useRef<string | null>(null);
  agreementsRef.current = agreements;
  addressRef.current = address;

  useEffect(() => {
    if (!schedulerOn) return;
    const id = setInterval(async () => {
      if (runningRef.current) return;
      const me = (addressRef.current || "").toLowerCase();
      if (!me) return;
      const ag = agreementsRef.current.find(
        (a) =>
          a.creator === me &&
          a.status === "active" &&
          a.checkpoints[a.current_index] &&
          a.checkpoints[a.current_index].status === "pending"
      );
      if (!ag) return;
      const cp = ag.checkpoints[ag.current_index];
      runningRef.current = true;
      setAutoKey(ag.agreement_id + "#" + cp.index);
      setSchedulerLog((l) => [new Date().toLocaleTimeString() + " — reviewing " + ag.agreement_id + " · checkpoint " + cp.index + "…", ...l].slice(0, 8));
      try {
        const v = await executeReview(me, ag.agreement_id, cp.index, cp.evidence_url, cp.criteria);
        setSchedulerLog((l) => [new Date().toLocaleTimeString() + " — " + ag.agreement_id + " · checkpoint " + cp.index + " → " + v.outcome + " " + Number(v.fulfillment_pct) + "%", ...l].slice(0, 8));
        await refresh();
      } catch (e: any) {
        setSchedulerLog((l) => [new Date().toLocaleTimeString() + " — error: " + (e?.message ?? String(e)), ...l].slice(0, 8));
      } finally {
        runningRef.current = false;
        setAutoKey(null);
      }
    }, 12000);
    return () => clearInterval(id);
  }, [schedulerOn, refresh]);

  async function mintSelf() {
    if (!address) return;
    setMinting(true);
    setError(null);
    try {
      await mint(address, address, 10000);
      await refresh();
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setMinting(false);
    }
  }

  return (
    <div className={"steward" + (view === "home" ? " wide" : "")}>
      <header className="masthead">
        <div className="wordmark">STEWARD</div>
        <div className="tagline">Treasury doesn't end at approval. Steward begins there.</div>
        <nav className="masthead-nav">
          <button className={"navlink" + (view === "home" ? " active" : "")} onClick={() => setView("home")}>Home</button>
          <button className={"navlink" + (view === "ledger" ? " active" : "")} onClick={() => setView("ledger")}>Ledger</button>
          <button className={"navlink" + (view === "guide" ? " active" : "")} onClick={() => setView("guide")}>Guide</button>
          <button className={"navlink" + (view === "how" ? " active" : "")} onClick={() => setView("how")}>How it works</button>
        </nav>
      </header>

      {view !== "home" && <section className="bar">
        {address ? (
          <div className="wallet">
            <span className={"mode-badge mode-" + mode}>{mode}</span>
            <Copyable text={address} display={address.slice(0, 6) + "…" + address.slice(-4)} className="mono" />
            {balance !== null && <span className="balance mono">{balance} genUSDC</span>}
            <button onClick={mintSelf} disabled={minting || loading}>{minting ? "Minting…" : "Mint 10000"}</button>
            <button onClick={refresh} disabled={loading || minting}>{loading ? "Reading…" : "Refresh"}</button>
            {mode === "demo" && <button className="link" onClick={newDemoWallet} disabled={loading || minting}>new demo wallet</button>}
            <button className="link" onClick={disconnect} disabled={loading || minting}>disconnect</button>
          </div>
        ) : (
          <div className="wallet">
            <button className="primary" onClick={connectMetaMask}>Connect MetaMask</button>
            <button onClick={useDemo}>Demo mode</button>
          </div>
        )}
      </section>}

      {error && <div className="error mono">{error}</div>}

      {view === "home" ? (
        <Landing onLaunch={() => setView("ledger")} onHow={() => setView("how")} />
      ) : view === "how" ? (
        <HowItWorks />
      ) : view === "guide" ? (
        <Guide />
      ) : (
        <>
          {address && (
            <div className="control-row">
              <label className="sched-toggle">
                <input type="checkbox" checked={schedulerOn} onChange={(e) => setSchedulerOn(e.target.checked)} />
                autonomy scheduler {schedulerOn ? "· on" : "· off"}
              </label>
              {schedulerOn && <span className="muted sched-note">Due reviews on your active agreements run automatically — no manual click. V1: runs while this tab is open.</span>}
            </div>
          )}
          {schedulerLog.length > 0 && (
            <div className="scheduler-log mono">
              {schedulerLog.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          )}

          {address && <CreateAgreement account={address} onCreated={refresh} />}

          <main>
            <div className="section-head">
              <h2 className="section-title">Standing Orders</h2>
              {address && (
                <button className="link" onClick={() => setShowAll((s) => !s)} disabled={loading}>
                  {showAll ? "show mine" : "show all on-chain"}
                </button>
              )}
            </div>
            {address && agreements.length === 0 && !loading && !showAll && (
              <div className="quickstart">
                <h3>Quick start</h3>
                <ol>
                  <li>Click <strong>Mint 10000</strong> (top right) to fund your demo balance.</li>
                  <li>Click <strong>+ New Standing Order</strong>, then <strong>load sample grant</strong> to prefill a real example — or write your own.</li>
                  <li><strong>Create &amp; lock</strong> it. It's addressed to you, so click <strong>Accept agreement</strong>.</li>
                  <li>As the creator, click <strong>Reserve</strong> to lock the capital on-chain.</li>
                  <li>Click <strong>Run Review</strong> on each checkpoint — or flip the <strong>autonomy scheduler</strong> on and let it run itself.</li>
                </ol>
                <p className="muted">Want the full picture? Open <strong>How it works</strong> in the header.</p>
              </div>
            )}
            {address && agreements.length === 0 && !loading && showAll && (
              <p className="muted">No agreements on-chain yet.</p>
            )}
            {!address && (
              <p className="muted">New here? Click <strong>Demo mode</strong> above — you get a free test wallet instantly, no MetaMask needed. Then follow the quick start.</p>
            )}
            <div className="ledger">
              {agreements.map((a) => (
                <AgreementCard key={a.agreement_id} agreement={a} address={address as string} onChanged={refresh} autoBusy={schedulerOn} autoKey={autoKey} />
              ))}
            </div>
          </main>
        </>
      )}
    </div>
  );
}
