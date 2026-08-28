# Steward — Contract Tests

These tests exercise the **real** `steward_verifier.py` and `steward_reserve.py`
contracts as a live two-contract system: real cross-contract calls, the real
review-epoch logic, and the real settlement path. There are **no skips and no
copied-logic stand-ins** — every assertion runs against the deployed contract
code in a local GenVM.

## What they prove

| Test | Property |
|---|---|
| `test_review_refused_when_not_active` | A **premature** review (agreement not yet active) is refused, so no verdict can be produced to settle. |
| `test_review_refused_for_non_current_checkpoint` | A review of a **non-current** checkpoint is refused. |
| `test_second_review_in_same_epoch_refused` | Only **one verdict per review epoch** — a re-roll inside the same epoch is refused. |
| `test_settlement_is_permissionless` | A party who is **neither creator nor owner** can drive `apply_verdict`. |
| `test_malformed_first_case_does_not_strand` | A **malformed** first verdict does not settle and does not strand: it advances the epoch, reopens the checkpoint, and leaves reserved capital untouched. |
| `test_stale_epoch_verdict_cannot_settle` | A **pre-queued / stale-epoch** verdict is rejected by epoch number; only the current epoch's verdict can settle. |

The happy path — a valid `Release` verdict settling and paying out, driven by a
non-creator — is verified on the live studionet deployment (the contracts are
deployed and a full agreement is settled through the UI).

## Why glsim (not the offline direct runner)

Steward is two contracts that call each other (the verifier reads the reserve to
pull canonical checkpoint state; the reserve reads the verifier's verdict to
settle). Cross-contract calls are only resolved by **glsim**, the in-process
local simulator, so the suite runs there. The verifier's review path calls
`gl.eq_principle.prompt_non_comparative(...)`; the tests drive that through
glsim's validator mock so verdict content is deterministic, while the contract
logic under test runs for real.

## Running the tests

```bash
# 1. Install the pinned runner
pip install "genlayer-test[sim]==0.29.2"

# 2. Seed the genvm SDK cache once (online; caches v0.2.16, then runs offline)
pytest tests/test_00_seed.py

# 3. Start the local simulator (separate terminal)
python run_glsim.py --port 4001
#    then point gltest.config.yaml's localnet url at that port

# 4. Run the suite
pytest tests/test_steward_guards.py -q
```

Expected: `6 passed`.

## About `conftest.py` and `run_glsim.py`

Both files contain **only local-simulator shims for Windows and test
determinism** — they do not touch the contracts or change any assertion:

- `conftest.py` swallows a Windows-only `os.unlink` sharing-violation raised by
  the direct runner's temp-file cleanup (the file is intentionally left open via
  the inherited fd 0).
- `run_glsim.py` launches glsim with Windows file-sharing fixes, keeps the
  bundled `genlayer` SDK importable across VM activations and cross-contract
  reloads, runs the leader once with unanimous validators (single-leader
  consensus, so cross-transaction state still persists and a genuine second
  review in the same epoch still reverts), and marshals the mocked LLM result as
  a raw string to match real GenLayer.

None of these affect contract behaviour; they exist so the same real contract
code runs under the local simulator on Windows.
