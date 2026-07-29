export function HowItWorks() {
  return (
    <div className="howto">
      <section className="howto-block">
        <h2>What Steward is</h2>
        <p>Steward is an autonomous execution layer for software-development grants on the GenLayer Studio Network. A DAO approves a grant and, instead of sending the full amount, Steward reserves it and releases capital tranche-by-tranche only when GenLayer validators reach consensus that predefined, machine-observable Verification Checkpoints have genuinely been satisfied. Partial fulfilment releases proportionally. No human decides when the money moves.</p>
      </section>

      <section className="howto-block">
        <h2>The lifecycle</h2>
        <p>A creator defines an ordered list of Verification Checkpoints — each with a locked evidence source (a repository, release, package, or deployment URL), locked criteria, and a tranche amount — and finalises them on-chain. The recipient accepts the same checkpoints; from that point neither side can move the goalposts. The creator reserves genUSDC into the agreement, and work begins.</p>
        <p>When a checkpoint is reviewed, the verifier contract fetches the locked evidence source, reaches validator consensus on whether the locked criteria are met and to what percentage, and the reserve contract moves capital by that verdict — released to the recipient, withheld, or revoked to the treasury. The reserve drains checkpoint by checkpoint, visible at a glance in the ledger.</p>
      </section>

      <section className="howto-block">
        <h2>Why this needs GenLayer</h2>
        <p>A CI pipeline can mechanically check that a tag exists or that tests pass. It cannot reason about whether a release is genuine substance or padding — five hundred empty commits, or a repository that technically contains the files but does not implement what the checkpoint required. Steward does both: the mechanical checks and a consensus judgment over the same fetched evidence. Remove the consensus and you are back to a trusted committee deciding when money moves — the exact intermediary Steward replaces. The consensus is the execution layer.</p>
      </section>

      <section className="howto-block">
        <h2>The five outcomes</h2>
        <p>Every review resolves to one of five outcomes. <strong>Release</strong> pays the full tranche when the criteria are essentially met. <strong>Reduce</strong> releases proportionally to the fulfilment percentage and withholds the remainder when a checkpoint is partially met. <strong>Pause</strong> holds when the evidence is unreachable or too thin to judge, to be reviewed again later. <strong>Escalate</strong> returns a genuinely ambiguous case to the DAO. <strong>Cancel</strong> revokes the remaining allocation back to the treasury when a checkpoint is clearly unmet or looks like a gaming attempt.</p>
      </section>

      <section className="howto-block">
        <h2>V1 limitations, stated honestly</h2>
        <p><strong>Settlement is bound to the verdict.</strong> No caller-supplied data drives a review or a settlement. The verifier reads each checkpoint's locked evidence source and criteria directly from the reserve, so a reviewer cannot feed it different inputs. To settle, apply_verdict is given only a case id; the reserve reads that verdict from the verifier on-chain, confirms it was produced against this checkpoint's exact locked source and complete criteria, authenticates the transaction sender, accepts only the most recent verdict for that checkpoint, and moves capital strictly by the verifier's stored fulfilment percentage and outcome. A relayer cannot fake the number, spoof an identity, point at a different repository, or submit an older, more favourable verdict.</p>
        <p><strong>Completion and held capital.</strong> A checkpoint can Pause (re-review later) or Escalate (return to the DAO). Held capital is never stranded: the creator can cancel an active agreement at any time, which returns the remaining reserved capital to the treasury and closes the order — so paused or escalated campaigns always have an exit.</p>
        <p><strong>Scope.</strong> Steward V1 covers software-development grants only. Every checkpoint condition must be web-verifiable from developer artifacts — repositories, commits, releases and tags, package registries, deployment URLs, and CI status. Offline or subjective conditions are out of scope, and the checkpoint builder enforces verifiable evidence sources.</p>
        <p><strong>Evidence window.</strong> The verifier reads a bounded slice of each fetched source, so criteria should reference facts that appear within the first portion of the evidence rather than deep inside a long document.</p>
        <p><strong>Scheduler.</strong> An autonomy scheduler is built in: toggling it on runs due reviews on your active agreements automatically, checkpoint by checkpoint, with no manual click — the reviews and the capital movements they trigger happen on their own. In V1 it is a client-side loop that runs while the app tab is open; a server-side or on-chain trigger is the V2 path, and the manual Run Review button works independently of it.</p>
        <p><strong>Signing and gas.</strong> The Studio Network is a gasless testnet, so Demo mode gives each browser its own fresh burner wallet with no funding required — a real, isolated identity per visitor. MetaMask is also supported for a persistent wallet. Broader multi-wallet support is on the genlayer-js roadmap. genUSDC is a mock settlement token for the testnet.</p>
        <p><strong>The minority note.</strong> Each verdict preserves a minority position — the strongest reason a dissenting validator might disagree — as the model's steelman of the dissent, not a transcript of validator votes.</p>
      </section>
    </div>
  );
}
