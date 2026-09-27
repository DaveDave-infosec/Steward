# Steward — Contract Tests

These tests exercise the **real** `steward_verifier.py` and `steward_reserve.py`
contracts as a live two-contract system: real cross-contract calls, the real
review schedule, the real settlement path. There are **no skips and no
copied-logic stand-ins** — every assertion runs against the deployed contract
code in a local GenVM.

`pytest tests/test_steward_guards.py -q` → **17 passed**.

## Settlement guards

| Test | Property |
|---|---|
| `test_review_refused_when_not_active` | A review of a not-yet-active agreement is refused, so no verdict can exist to settle. |
| `test_review_refused_for_non_current_checkpoint` | A review of a non-current checkpoint is refused. |
| `test_second_review_in_same_epoch_refused` | Only **one verdict per review epoch** — a re-roll inside the same epoch is refused. |
| `test_settlement_is_permissionless` | A party who is **neither creator nor owner** can drive `apply_verdict`. |
| `test_malformed_first_case_does_not_strand` | A malformed verdict neither settles nor strands: it advances the epoch, reopens the checkpoint, and leaves reserved capital untouched. |
| `test_stale_epoch_verdict_cannot_settle` | A pre-queued / stale-epoch verdict is rejected by epoch number. |

## Scheduled due times

Every activated checkpoint is given an **explicit** due time — no implicit "0
means due now" sentinel — and that schedule is enforced in **both** due
discovery and review execution.

| Test | Property |
|---|---|
| `test_activation_schedules_an_explicit_due_time` | Activation writes a real `next_review_at` timestamp, and the checkpoint is then due. |
| `test_non_active_agreement_is_not_due` | A non-active agreement is never offered to a keeper. |
| `test_future_due_time_blocks_discovery_and_review` | A future due time hides the checkpoint from `get_due()` **and** makes `run_review` revert — premature reviews are rejected at execution, not merely hidden. |

## Reserve-instance scoping

Agreement ids restart per reserve deployment, so a shared verifier must scope
its state by reserve. These cover a real bug found and fixed in V3.1:

| Test | Property |
|---|---|
| `test_verdict_cannot_settle_a_different_reserve` | A verdict minted against reserve A **cannot** settle reserve B, even when both hold an `agr_0` with the same locked URL, criteria and epoch. |
| `test_epoch_key_is_scoped_per_reserve` | Reserve A consuming a review epoch does not block reserve B's identical slot. |

## Outcome matrix — state and balance movement

Tranche 1000, protocol fee 100 bps, with a **distinct fee wallet** so every
movement is unambiguous.

| Test | Expected result |
|---|---|
| `test_outcome_release_pays_the_full_tranche` | released, 100%; recipient +990, fee wallet +10, creator +0; agreement completed. |
| `test_outcome_reduce_pays_proportionally_and_withholds_the_rest` | reduced, 50%; recipient +495, fee wallet +5, creator +500 withheld back; agreement completed. |
| `test_outcome_pause_holds_capital_and_reopens` | paused, epoch advances, reserved stays 1000, no balance moves. |
| `test_outcome_escalate_holds_capital_and_reopens` | escalated, epoch advances, reserved stays 1000, no balance moves. |
| `test_outcome_cancel_refunds_the_creator` | cancelled; creator refunded the full 1000, recipient and fee wallet unpaid. |
| `test_inconsistent_outcome_does_not_settle` | A Release claimed at 10% violates the documented Release >= 85 relationship: nothing is paid and the checkpoint reopens. |

## Verified live on studionet

A permissionless keeper — an address that is neither creator nor owner —
reviewed and settled an agreement end to end with no human trigger:

- autonomous review: `0xcc408f36f425862010544da18f246e415706a85b15e2a6264e92587c5cf13370`
- autonomous settlement: `0xe380cf6a9f24128636b29af52e14b083f342a2494c499ab09a3309d5ffed5c6b`

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
pip install "genlayer-test[sim]==0.29.2"
pytest tests/test_00_seed.py          # once, online: caches the v0.2.16 SDK
python run_glsim.py --port 4001       # separate terminal
pytest tests/test_steward_guards.py -q
```

`gltest.config.yaml` points localnet at port 4001 to match.

## About `conftest.py` and `run_glsim.py`

Both contain **only local-simulator shims for Windows and test determinism** —
they never touch the contracts or change an assertion: a Windows `os.unlink`
sharing-violation swallow, Windows file-sharing fixes, keeping the bundled
`genlayer` SDK importable across VM activations and cross-contract reloads,
running the leader once with unanimous validators, and marshalling the mocked
LLM result as a raw string to match real GenLayer.
