# Steward — Autonomous Execution for Developer Grants

**Treasury doesn't end at approval. Steward begins there.**

Steward is an autonomous execution layer for software-development grants on the GenLayer Studio Network. A DAO approves a grant and, instead of sending the full amount, Steward reserves it and releases capital tranche-by-tranche — only when GenLayer validators reach consensus that predefined, machine-observable **Verification Checkpoints** have genuinely been satisfied. Partial fulfilment releases proportionally. **No human decides when the money moves.**

## The load-bearing idea

When consensus reaches a verdict, something irreversible and valuable happens automatically: the reserve contract releases, withholds, or revokes real capital by that consensus, and state finalises on-chain. Remove the consensus and you are back to a trusted committee deciding when money moves — the exact intermediary Steward replaces. **The consensus is the execution layer.**

A CI pipeline can mechanically check that a tag exists or that tests pass. It cannot reason about whether a release is genuine substance or padding — 500 empty commits, or a repo that contains the files but does not implement what the checkpoint required. Steward does both: the mechanical checks *and* a consensus judgment over the same fetched evidence. That combination is the "why GenLayer and not a GitHub Action" answer.

## How it works

1. **Create** — a creator defines an ordered list of Verification Checkpoints, each with a locked evidence source (repo / release / package / deployment URL), locked criteria, and a tranche amount, and finalises them on-chain.
2. **Accept** — the recipient accepts the same checkpoints. Neither side can move the goalposts afterward.
3. **Reserve** — the creator reserves genUSDC into the agreement.
4. **Review** — a review (manual, or fired by the autonomy scheduler) has the verifier contract fetch the locked source, reach validator consensus on whether the criteria are met and to what percentage, and produce a verdict.
5. **Execute** — the reserve contract moves capital by that verdict: **Release**, **Reduce** (proportional), **Pause**, **Escalate**, or **Cancel** (revoke remaining to treasury).

## Architecture

- **`contracts/steward_verifier.py`** — the GenLayer Intelligent Contract. Fetches each checkpoint's locked evidence source deterministically (`gl.eq_principle.strict_eq` + `gl.nondet.web.get`) and reasons over it against the locked criteria by validator consensus (`gl.eq_principle.prompt_non_comparative`), producing a fulfilment percentage, outcome, reasoning, and a preserved minority note. It never touches funds. Verdicts are stored in flat parallel TreeMaps.
- **`contracts/steward_reserve.py`** — the execution layer. Holds genUSDC (an embedded mock settlement token), records agreements and their locked checkpoints, and on each verdict applies the outcome — proportional release, withhold, or revoke — skimming a protocol fee. Only this contract moves money, and only by a verdict.
- **`frontend/`** — React + TypeScript + Vite, using `genlayer-js`. The "Standing Orders" institutional ledger UI.

### Deployment

| | |
|---|---|
| Network | GenLayer Studio Network |
| Chain ID | 61999 (0xF22F) |
| Reserve contract | `0x610F1D7dD5920499E06f8E1a82fe459E2B793dd3` |
| Verifier contract | `0x1e4Eba962BFF2b118Bc19d8d5304de92f927b622` |

genUSDC is a mock settlement token for the testnet.

## Running the frontend
cd frontend
npm install
npm run dev

Click **Demo mode** for a free, per-browser test wallet (studionet is gasless — no funding needed), or connect MetaMask. The **Guide** and **How it works** tabs walk through the full flow and the honest V1 limitations.

## V1 limitations, stated honestly

- **Execution relay.** The verdict is relayed into the reserve by an owner-or-creator call rather than an automatic contract-to-contract trigger; the verdict values come only from validator consensus and cannot be changed by the relayer. A trustless verifier-to-reserve bridge is the V2 target.
- **Scope.** Software-development grants only; every checkpoint condition must be web-verifiable from developer artifacts.
- **Evidence window.** The verifier reads a bounded slice of each fetched source.
- **Scheduler.** The autonomy scheduler is a client-side loop that runs while the app tab is open; a server-side or on-chain trigger is the V2 path.
- **Signing.** MetaMask (via the GenLayer Snap) and gasless per-browser demo burners are supported; broader multi-wallet support is on the genlayer-js roadmap.

Built on GenLayer.
