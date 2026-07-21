import { useEffect, useState } from "react";
import { loadStats } from "./lib/stats";

function CountUp({ value, duration = 1100 }: { value: number; duration?: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!value) { setN(0); return; }
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(value * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{n.toLocaleString()}</>;
}

export function Landing({ onLaunch, onHow }: { onLaunch: () => void; onHow: () => void }) {
  const [stats, setStats] = useState<{ agreements: number; released: number; verdicts: number } | null>(null);

  useEffect(() => {
    let alive = true;
    loadStats().then((s) => { if (alive) setStats(s); }).catch(() => { /* ignore */ });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const els = Array.from(document.querySelectorAll(".landing .reveal"));
    if (typeof IntersectionObserver === "undefined") {
      els.forEach((e) => e.classList.add("reveal-in"));
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("reveal-in");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((e) => obs.observe(e));
    return () => obs.disconnect();
  }, []);

  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-copy reveal">
          <span className="pill">● Live on GenLayer Studio</span>
          <h1 className="hero-title">Grants get paid on trust. <em>This one pays on proof.</em></h1>
          <p className="hero-sub">A DAO approves a grant and Steward reserves it instead of sending it. Capital releases tranche by tranche — only when GenLayer validators reach consensus that the work actually landed. Partial delivery pays partially. Padding pays nothing.</p>
          <div className="hero-cta">
            <button className="primary big" onClick={onLaunch}>Launch app <span className="arrow">→</span></button>
            <button className="btn-outline big" onClick={onHow}>How it works</button>
          </div>
          <div className="stats">
            <div className="stat"><span className="stat-num">{stats ? <CountUp value={stats.agreements} /> : "—"}</span><span className="stat-label">Standing orders</span></div>
            <div className="stat"><span className="stat-num">{stats ? <CountUp value={stats.released} /> : "—"}</span><span className="stat-label">genUSDC released</span></div>
            <div className="stat"><span className="stat-num">{stats ? <CountUp value={stats.verdicts} /> : "—"}</span><span className="stat-label">Verdicts issued</span></div>
          </div>
        </div>

        <aside className="preview reveal">
          <div className="preview-head mono">agr_2 · checkpoint 1 · <span className="pv-reduced">reduced · 50%</span></div>
          <div className="pv-bar"><span className="pv-seg pv-green" /><span className="pv-seg pv-ochre" /></div>
          <div className="pv-amounts mono">released 198 · withheld 200</div>
          <p className="pv-quote">“The project documents proportional, consensus-based escrow settlement, but there is no evidence of a tagged v1.0.0 release.”</p>
          <p className="pv-minority">Minority note: the deployment address could suggest a release exists, but the criteria requires a tagged v1.0.0.</p>
        </aside>
      </section>

      <section className="lsection">
        <div className="reveal">
          <span className="eyebrow">How it works</span>
          <h2 className="lsection-title">Three steps from approval to settlement.</h2>
        </div>
        <div className="steps">
          <div className="step reveal">
            <span className="step-num mono">01</span>
            <h3>Lock the checkpoints</h3>
            <p>The DAO defines each milestone as a locked evidence source and locked criteria with its own tranche. The recipient accepts the same terms. Neither side can move the goalposts afterwards.</p>
          </div>
          <div className="step reveal">
            <span className="step-num mono">02</span>
            <h3>Validators verify the work</h3>
            <p>At review, GenLayer validators fetch the locked source, run the mechanical checks, and judge whether the work genuinely implements what was required — not merely whether files exist.</p>
          </div>
          <div className="step reveal">
            <span className="step-num mono">03</span>
            <h3>Capital moves by the verdict</h3>
            <p>The reserve reads that verdict on-chain and releases, reduces, or revokes the tranche accordingly. No human sets the number.</p>
          </div>
        </div>
      </section>

      <section className="lsection">
        <div className="reveal">
          <h2 className="lsection-title">What the verifier catches.</h2>
        </div>
        <div className="catches">
          <div className="catch reveal"><h3>Padding commits</h3><p>Five hundred commits that change nothing. The tag exists; the work doesn't.</p></div>
          <div className="catch reveal"><h3>Files without function</h3><p>A repository that technically contains the files but never implements what the checkpoint required.</p></div>
          <div className="catch reveal"><h3>Over-claimed releases</h3><p>“Audited v2.0.0” on a repository whose tag list is empty.</p></div>
          <div className="catch reveal"><h3>Partial delivery</h3><p>Code shipped, docs missing. Pays proportionally instead of all-or-nothing.</p></div>
          <div className="catch reveal"><h3>Wrong evidence</h3><p>A verdict produced against a different repository is refused on-chain.</p></div>
          <div className="catch reveal"><h3>Verdict shopping</h3><p>Run the review ten times; only the newest verdict can settle, and every attempt is public.</p></div>
        </div>
      </section>

      <section className="lsection">
        <div className="reveal">
          <span className="eyebrow">Questions</span>
          <h2 className="lsection-title">What people ask before their first grant.</h2>
        </div>
        <div className="faq">
          <div className="faq-row reveal"><div className="faq-q">What do I need to use it?</div><div className="faq-a">Nothing. Demo mode mints a free wallet in your browser and the Studio Network is gasless, so there is no funding step. MetaMask is supported if you prefer a persistent wallet.</div></div>
          <div className="faq-row reveal"><div className="faq-q">Who decides how much gets released?</div><div className="faq-a">Nobody. Validators return a fulfilment percentage and an outcome, and the reserve settles by that number alone.</div></div>
          <div className="faq-row reveal"><div className="faq-q">What if the work is only half done?</div><div className="faq-a">It pays half. Partial fulfilment releases proportionally and withholds the remainder, instead of forcing an all-or-nothing decision.</div></div>
          <div className="faq-row reveal"><div className="faq-q">Can the payer rig the outcome?</div><div className="faq-a">No. Settlement takes only a case id. The reserve reads the verdict from the verifier itself, requires it to match the checkpoint's exact locked source and full criteria, authenticates the transaction sender, and accepts only the most recent verdict.</div></div>
          <div className="faq-row reveal"><div className="faq-q">What can it verify?</div><div className="faq-a">Anything machine-observable from developer artifacts: repositories, commits, tags and releases, package registries, deployment URLs, CI status.</div></div>
          <div className="faq-row reveal"><div className="faq-q">Why does this need GenLayer?</div><div className="faq-a">A CI pipeline can confirm a tag exists. It cannot tell real substance from padding. Validators reason about that and reach consensus, and the consensus is what moves the money.</div></div>
        </div>
      </section>

      <section className="closing reveal">
        <h2>Stop paying on promises. <em>Start paying on proof.</em></h2>
        <p>The next grant you approve doesn't have to leave your treasury on faith.</p>
        <button className="primary big" onClick={onLaunch}>Launch app <span className="arrow">→</span></button>
      </section>
    </div>
  );
}
