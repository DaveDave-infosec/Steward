# Steward — Contract Tests

These tests exercise the **real** `steward_verifier.py` and `steward_reserve.py`
contracts as a live two-contract system: real cross-contract calls, the real
review-epoch logic, the real settlement path, and the keeper's due surface.
There are **no skips and no copied-logic stand-ins** — every assertion runs
against the deployed contract code in a local GenVM.

`pytest tests/test_steward_guards.py -q` → **11 passed**.

## Settlement guards

| Test | Property |
|---|---|
| `test_review_refused_when_not_active` | A **premature** review (agreement not yet active) is refused, so no verdict can be produced to settle. |
| `test_review_refused_for_non_current_checkpoint` | A review of a **non-current** checkpoint is refused. |
| `test_second_review_in_same_epoch_refused` | Only **one verdict per review epoch** — a re-roll inside the same epoch is refused. |
| `test_settlement_is_permissionless` | A party who is **neither creator nor owner** can drive `apply_verdict`. |
| `test_malformed_first_case_does_not_strand` | A **malformed** first verdict does not settle and does not strand: it advances the epoch, reopens the checkpoint, and leaves reserved capital untouched. |
| `test_stale_epoch_verdict_cannot_settle` | A **pre-queued / stale-epoch** verdict is rejected by epoch number. |

## Keeper due surface

| Test | Property |
|---|---|
| `test_active_checkpoint_is_due` | `get_due()` surfaces an active agreement's current checkpoint. |
| `test_non_active_agreement_is_not_due` | A non-active agreement is never offered to a keeper. |
| `test_backoff_removes_checkpoint_from_due` | After a reopen, `next_review_at` backs the checkpoint off so a keeper does not hammer it. |

## Reserve-instance scoping

Agreement ids restart per reserve deployment, so a shared verifier must scope its
state by reserve. These two cover a real bug found and fixed in V3.1:

| Test | Property |
|---|---|
| `test_verdict_cannot_settle_a_different_reserve` | A verdict minted against reserve A **cannot** settle reserve B, even when both hold an `agr_0` with the same locked URL, criteria and epoch. |
| `test_epoch_key_is_scoped_per_reserve` | Reserve A consuming a review epoch **does not block** reserve B's identical slot on the same verifier. |

## Verified live on studionet

A permissionless keeper — an address that is neither creator nor owner — reviewed
and settled an agreement end-to-end with no human trigger:

- autonomous review: `0xecf68dde8fe5b508a0e59adc7963f578b685d65f9196f3c8f91523bddf5a080e`
- autonomous settlement: `0x191ed799a19d664d9c569fa237473dcbd5f1acb62b8267929c109b4e5ba304f6`

## Why glsim (not the offline direct runner)

Steward is two contracts that call each other (the verifier reads the reserve for
canonical checkpoint state; the reserve reads the verifier's verdict to settle).
Cross-contract calls are only resolved by **glsim**, the in-process local
simulator. The verifier's review path calls
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

# 4. Run the suite
pytest tests/test_steward_guards.py -q
```

`gltest.config.yaml` points localnet at port 4001 to match.

## About `conftest.py` and `run_glsim.py`

Both contain **only local-simulator shims for Windows and test determinism** —
they never touch the contracts or change an assertion:

- `conftest.py` swallows a Windows-only `os.unlink` sharing violation from the
  direct runner's temp-file cleanup.
- `run_glsim.py` launches glsim with Windows file-sharing fixes, keeps the
  bundled `genlayer` SDK importable across VM activations and cross-contract
  reloads, runs the leader once with unanimous validators (cross-transaction
  state still persists, so a genuine second review in the same epoch still
  reverts), and marshals the mocked LLM result as a raw string to match real
  GenLayer.
