export function Guide() {
  return (
    <div className="howto">
      <section className="howto-block">
        <h2>1 · Get a wallet</h2>
        <p>Click <strong>Demo mode</strong> for a free test wallet — created instantly in your browser, no MetaMask and no funding needed. Each browser gets its own wallet; use <strong>new demo wallet</strong> anytime for a fresh identity, or <strong>Connect MetaMask</strong> for a persistent one.</p>
      </section>
      <section className="howto-block">
        <h2>2 · Fund it</h2>
        <p>Click <strong>Mint 10000</strong> to give your wallet genUSDC — the mock settlement token you'll reserve and release.</p>
      </section>
      <section className="howto-block">
        <h2>3 · Draft a grant</h2>
        <p>Click <strong>+ New Standing Order</strong>. The fastest way to see it work is <strong>load sample grant</strong>, which prefills a real, working example. Otherwise fill it in yourself: a recipient address, a max allocation, and one or more <strong>Verification Checkpoints</strong> — each a locked evidence URL (a GitHub API endpoint, a raw README, a package page), the criteria to check it against, and a tranche amount. Press <strong>Create &amp; lock</strong>; from that moment the criteria and sources are immutable.</p>
      </section>
      <section className="howto-block">
        <h2>4 · Accept the terms</h2>
        <p>The <strong>recipient</strong> reviews the locked checkpoints and clicks <strong>Accept agreement</strong>. In the single-wallet demo the recipient is you (the field is prefilled with your address). Neither side can change the checkpoints after acceptance.</p>
      </section>
      <section className="howto-block">
        <h2>5 · Reserve the capital</h2>
        <p>The <strong>creator</strong> clicks <strong>Reserve</strong> to lock the genUSDC into the agreement. It is now held under condition — the slate portion of the capital bar.</p>
      </section>
      <section className="howto-block">
        <h2>6 · Run the reviews</h2>
        <p>Click <strong>Run Review</strong> on the current checkpoint. GenLayer validators fetch the locked source, reach consensus on whether the criteria are met and to what percentage, and the reserve moves capital by that verdict — released to the recipient (green), withheld (ochre), or revoked to the treasury (oxblood). Each verdict shows its reasoning and a preserved minority note. Repeat per checkpoint and watch the reserve drain.</p>
      </section>
      <section className="howto-block">
        <h2>Let it run itself</h2>
        <p>Flip the <strong>Autonomy scheduler</strong> toggle above the ledger and the due review on each active agreement you created runs automatically — no clicking Run Review. It works through the checkpoints one at a time, logging each verdict with a timestamp, and stops when the agreement resolves. This is the autonomy dimension: the reviews, and the capital movements they trigger, happen without a human pressing a button. In V1 it runs while this tab is open; the manual button works independently.</p>
      </section>
      <section className="howto-block">
        <h2>Try the two-party flow</h2>
        <p>To see the real DAO-to-developer path, open a second browser or incognito window for the recipient and enter Demo mode there — it gets a different wallet. Copy that wallet's address (click it), and in the first browser use it as the <strong>recipient</strong> when creating a grant. The recipient's browser will see the incoming Standing Order and can Accept it, and the released funds land in their wallet — capital moving to a genuinely different party by consensus alone.</p>
      </section>
      <section className="howto-block">
        <h2>Handy details</h2>
        <p>Click any address to copy it. <strong>show all on-chain</strong> lists every agreement, not just yours. <strong>disconnect</strong> and <strong>new demo wallet</strong> switch identities. For the concept and honest V1 limitations, see <strong>How it works</strong>.</p>
      </section>
    </div>
  );
}
