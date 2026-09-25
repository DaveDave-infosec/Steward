# Steward Keeper

A permissionless autonomous keeper. It polls the reserve's `get_due()` and, for every checkpoint that is ready, fires `run_review` (verifier) then `apply_verdict` (reserve) — so capital releases the moment a milestone is verifiably met, with no human trigger.

It holds no privilege: settlement is bound to the on-chain verdict, so the keeper can only trigger the pipeline, never change an outcome. Anyone can run one; if two race, the first wins and the rest no-op.

## Run

    cd keeper
    npm install
    # PowerShell:
    $env:RESERVE_ADDRESS="0xbeE3012AAb27a0b345a5d9e84971771891BCd573"
    $env:VERIFIER_ADDRESS="0x2e5c25330166a9B194F634fB2F860BE571CcA32A"
    node keeper.mjs          # continuous loop
    # single pass (cron/CI):  $env:ONCE="1"; node keeper.mjs

studionet is gasless, so no funding is needed. Set `KEEPER_PRIVATE_KEY` for a stable identity. See `.env.example`.

## Each pass
1. `get_due()` -> the checkpoints whose current review is due (past their backoff).
2. For each: `run_review` -> `get_latest_case_for` -> `apply_verdict`.
3. Pause/Escalate/malformed reopen with a backoff (retried next pass); Release/Reduce settle. Per-item errors are logged and skipped, never stopping the loop.
