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
5. **Execute** — settlement is permissionless: anyone can relay the verdict, and the reserve contract moves capital by it: **Release**, **Reduce** (proportional), **Pause**, **Escalate**, or **Cancel** (revoke remaining to treasury).

## Architecture

- **`contracts/steward_verifier.py`** — the GenLayer Intelligent Contract. Fetches each checkpoint's locked evidence source deterministically (`gl.eq_principle.strict_eq` + `gl.nondet.web.get`) and reasons over it against the locked criteria by validator consensus (`gl.eq_principle.prompt_non_comparative`), producing a fulfilment percentage, outcome, reasoning, and a preserved minority note. It never touches funds. Verdicts are stored in flat parallel TreeMaps.
- **`contracts/steward_reserve.py`** — the execution layer. Holds genUSDC (an embedded mock settlement token), records agreements and their locked checkpoints, and on each verdict applies the outcome — proportional release, withhold, or revoke — skimming a protocol fee. Only this contract moves money, and only by a verdict.
- **`frontend/`** — React + TypeScript + Vite, using `genlayer-js`. The "Standing Orders" institutional ledger UI.

### Deployment

| | |
|---|---|
| Network | GenLayer Studio Network |
| Chain ID | 61999 (0xF22F) |
| Reserve contract | `0xAeB509dA9D0e93Ef1979da953a194Ab81684f19A` |
| Verifier contract | `0x878daa116D116aa7B8660b3f97fB10349F625b8C` |

genUSDC is a mock settlement token for the testnet.

## Running the frontend
cd frontend
npm install
npm run dev

Click **Demo mode** for a free, per-browser test wallet (studionet is gasless — no funding needed), or connect MetaMask. The **Guide** and **How it works** tabs walk through the full flow and the honest limitations.

## Design and limitations, stated honestly

- **Settlement is bound to the verdict, not to any person.** `apply_verdict` takes only a case id: the reserve reads the verdict directly from the verifier contract on-chain (`gl.get_contract_at(...).view()`), requires it to have been produced against the checkpoint's exact locked evidence source and complete criteria, and settles strictly by the verifier's stored fulfilment percentage and outcome. Settlement is **permissionless** — the recipient, a keeper, or any unrelated address can relay a verdict; correctness comes from the binding, not the caller, so no one can stall a payment the verdict has already earned. Verdicts are **final**: the reserve accepts only the first verdict produced since the checkpoint last became reviewable, so re-running a review cannot replace a prior verdict with a more favourable one (a Pause or Escalate opens a fresh window, so legitimate retries still work). No one can fake the number, use a verdict from a different repository, or re-roll the outcome.
- **Cancellation is locked once capital is reserved.** An agreement can be cancelled only before capital is committed. Once it is active, capital moves only by verdict — the creator cannot pull funds back. Nothing is stranded, because every review resolves the checkpoint and returns withheld or revoked capital to the treasury.
- **Scope.** Software-development grants only; every checkpoint condition must be web-verifiable from developer artifacts.
- **Evidence window.** The verifier reads a bounded slice of each fetched source.
- **Scheduler.** The autonomy scheduler is a client-side convenience loop that runs while the app tab is open. Because settlement is permissionless, any external keeper or bot can drive reviews and settlements on-chain independently of it.
- **Signing.** MetaMask (via the GenLayer Snap) and gasless per-browser demo burners are supported; broader multi-wallet support is on the genlayer-js roadmap.

## Tests

The verifier/reserve guard logic is covered by a real two-contract test suite (glsim, in-process GenVM — no skips, no copied logic). See [TESTING.md](TESTING.md).

## Autonomous keeper (V3)

Settlement is permissionless, so an off-chain keeper can drive the whole pipeline with no human trigger: it polls the reserve's `get_due()` view and fires `run_review` -> `apply_verdict` for every checkpoint that is ready. Capital releases the moment a milestone is verifiably met. The keeper holds no privilege — it can only trigger verdict-bound settlement, never change it — so anyone can run one. See [keeper/](keeper/).

Built on GenLayer.
