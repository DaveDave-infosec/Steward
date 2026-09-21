# Steward Keeper

A permissionless autonomous keeper. It polls the reserve's `get_due()` and, for every checkpoint that is ready, fires `run_review` (verifier) then `apply_verdict` (reserve) — so capital releases the moment a milestone is verifiably met, with no human trigger.

It holds no privilege: settlement is bound to the on-chain verdict, so the keeper can only trigger the pipeline, never change an outcome. Anyone can run one; if two race, the first wins and the rest no-op.

## Run

    cd keeper
    npm install
    # PowerShell:
    $env:RESERVE_ADDRESS="0xAeB509dA9D0e93Ef1979da953a194Ab81684f19A"
    $env:VERIFIER_ADDRESS="0x878daa116D116aa7B8660b3f97fB10349F625b8C"
    node keeper.mjs          # continuous loop
    # single pass (cron/CI):  $env:ONCE="1"; node keeper.mjs

studionet is gasless, so no funding is needed. Set `KEEPER_PRIVATE_KEY` for a stable identity. See `.env.example`.

## Each pass
1. `get_due()` -> the checkpoints whose current review is due (past their backoff).
2. For each: `run_review` -> `get_latest_case_for` -> `apply_verdict`.
3. Pause/Escalate/malformed reopen with a backoff (retried next pass); Release/Reduce settle. Per-item errors are logged and skipped, never stopping the loop.
