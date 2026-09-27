"""
Steward guard, keeper-due, scoping and outcome tests — the REAL two-contract
flow on glsim. No skips, no copied logic.

Covers:
  - settlement guards (premature review, one verdict per epoch, permissionless
    settlement, malformed recovery, stale epoch),
  - the keeper due surface and explicitly scheduled due times (rejected in BOTH
    due discovery and review execution),
  - reserve-instance scoping of verifier state,
  - every valid outcome and the exact checkpoint state and balance movement it
    produces, plus an internally inconsistent verdict refusing to settle.

Run:  python run_glsim.py --port 4001    (separate terminal)
      pytest tests/test_steward_guards.py -q
"""

import json
import pytest
from gltest import (
    get_contract_factory,
    get_default_account,
    create_account,
    get_validator_factory,
)
from gltest.assertions import tx_execution_succeeded, tx_execution_failed

VERIFIER = "steward_verifier.py"
RESERVE = "steward_reserve.py"

CP_URL = "https://api.github.com/repos/DaveDave-infosec/Balance/contents/contracts"
CP_CRITERIA = (
    "The contracts directory contains the Balance Intelligent Contract as a "
    "Python source file (balance)."
)

MALFORMED_VERDICT = "not-json {oops"
EVIDENCE = '[{"name": "balance.py", "path": "contracts/balance.py", "size": 19056, "type": "file"}]'
SUBMITTER = "0x0000000000000000000000000000000000000000"

BIG_INTERVAL = 10_000_000_000  # ~317 years; pushes next_review_at far past "now"


def _verdict(outcome, pct, reasoning="judged from the locked evidence"):
    return json.dumps({
        "fulfillment_pct": pct,
        "outcome": outcome,
        "reasoning": reasoning,
        "minority_note": "",
    })


def _validators(vf, verdict):
    return [
        v.to_dict()
        for v in vf.batch_create_mock_validators(
            5,
            mock_llm_response={"nondet_exec_prompt": {"": verdict}},
            mock_web_response={"nondet_web_request": {"": {"body": EVIDENCE}}},
        )
    ]


def _ctx(vf, verdict=MALFORMED_VERDICT):
    return {"validators": _validators(vf, verdict)}


def _expect_revert(thunk):
    try:
        res = thunk()
    except Exception:
        return
    assert tx_execution_failed(res), "expected the transaction to revert, but it succeeded"


def _deploy_pair(acct):
    verifier = get_contract_factory(contract_file_path=VERIFIER).deploy(
        args=[acct.address], account=acct
    )
    reserve = get_contract_factory(contract_file_path=RESERVE).deploy(
        args=[acct.address, acct.address, 100, verifier.address], account=acct
    )
    assert tx_execution_succeeded(verifier.set_reserve(args=[reserve.address]).transact())
    assert verifier.get_reserve(args=[]).call().lower() == reserve.address.lower()
    return verifier, reserve


def _deploy_with_fee_wallet(acct, fee):
    """Deploy with a DISTINCT fee wallet so balance movements are unambiguous."""
    verifier = get_contract_factory(contract_file_path=VERIFIER).deploy(
        args=[acct.address], account=acct
    )
    reserve = get_contract_factory(contract_file_path=RESERVE).deploy(
        args=[acct.address, fee.address, 100, verifier.address], account=acct
    )
    assert tx_execution_succeeded(verifier.set_reserve(args=[reserve.address]).transact())
    return verifier, reserve


def _make_active(reserve, creator, recipient, n=1, tranche=1000, interval=0):
    total = tranche * n
    reserve.mint(args=[creator.address, total]).transact()
    reserve.create_agreement(args=[recipient.address, total]).transact()
    for _ in range(n):
        reserve.add_checkpoint(args=["agr_0", CP_URL, CP_CRITERIA, tranche, "once", interval]).transact()
    reserve.finalize_agreement(args=["agr_0"]).transact()
    reserve.connect(recipient).accept_agreement(args=["agr_0"]).transact()
    reserve.reserve_capital(args=["agr_0", total]).transact()
    return "agr_0"


def _review(verifier, vf, idx=0, verdict=MALFORMED_VERDICT):
    verifier.run_review(args=["agr_0", idx, SUBMITTER]).transact(
        transaction_context=_ctx(vf, verdict)
    )
    return verifier.get_latest_case_for(args=["agr_0", idx]).call()


def _settle(verifier, reserve, vf, verdict, idx=0):
    case_id = _review(verifier, vf, idx, verdict)
    return reserve.apply_verdict(args=[case_id]).transact()


def _bal(reserve, who):
    return int(reserve.balance_of(args=[who.address]).call())


def _due_ids(reserve):
    return [d["agreement_id"] for d in json.loads(reserve.get_due(args=[]).call())]


# ============================ settlement guards ============================

def test_review_refused_when_not_active():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)

    reserve.mint(args=[acct.address, 1000]).transact()
    reserve.create_agreement(args=[bob.address, 1000]).transact()
    reserve.add_checkpoint(args=["agr_0", CP_URL, CP_CRITERIA, 1000, "once", 0]).transact()
    reserve.finalize_agreement(args=["agr_0"]).transact()
    reserve.connect(bob).accept_agreement(args=["agr_0"]).transact()

    _expect_revert(
        lambda: verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )


def test_review_refused_for_non_current_checkpoint():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob, n=2)

    _expect_revert(
        lambda: verifier.run_review(args=["agr_0", 1, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )


def test_second_review_in_same_epoch_refused():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob)

    _review(verifier, vf)
    _expect_revert(
        lambda: verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )


def test_settlement_is_permissionless():
    acct = get_default_account()
    bob = create_account()
    carol = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob)

    case_id = _review(verifier, vf)
    assert tx_execution_succeeded(
        reserve.connect(carol).apply_verdict(args=[case_id]).transact()
    )
    assert reserve.get_checkpoint(args=["agr_0", 0]).call()["epoch"] == 2


def test_malformed_first_case_does_not_strand():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob)

    v_bad = _review(verifier, vf)
    assert verifier.get_verdict(args=[v_bad]).call()["parsed_ok"] == "no"

    assert tx_execution_succeeded(reserve.apply_verdict(args=[v_bad]).transact())
    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "pending"
    assert cp["epoch"] == 2
    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "active"
    assert ag["reserved"] == 1000


def test_stale_epoch_verdict_cannot_settle():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob)

    v_stale = _review(verifier, vf)
    assert tx_execution_succeeded(reserve.apply_verdict(args=[v_stale]).transact())
    assert reserve.get_checkpoint(args=["agr_0", 0]).call()["epoch"] == 2

    _review(verifier, vf)
    _expect_revert(lambda: reserve.apply_verdict(args=[v_stale]).transact())


# ==================== scheduled due times / keeper surface ====================

def test_activation_schedules_an_explicit_due_time():
    acct = get_default_account()
    bob = create_account()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob, interval=0)

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["next_review_at"] > 0
    assert "agr_0" in _due_ids(reserve)


def test_non_active_agreement_is_not_due():
    acct = get_default_account()
    bob = create_account()
    verifier, reserve = _deploy_pair(acct)

    reserve.mint(args=[acct.address, 1000]).transact()
    reserve.create_agreement(args=[bob.address, 1000]).transact()
    reserve.add_checkpoint(args=["agr_0", CP_URL, CP_CRITERIA, 1000, "once", 0]).transact()
    reserve.finalize_agreement(args=["agr_0"]).transact()
    reserve.connect(bob).accept_agreement(args=["agr_0"]).transact()

    assert _due_ids(reserve) == []


def test_future_due_time_blocks_discovery_and_review():
    """A premature review is hidden from due discovery AND rejected at execution."""
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob, interval=BIG_INTERVAL)

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["next_review_at"] > 0
    assert "agr_0" not in _due_ids(reserve)

    _expect_revert(
        lambda: verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )


# ==================== reserve-instance scoping of verifier state ====================

def _deploy_verifier(acct):
    return get_contract_factory(contract_file_path=VERIFIER).deploy(
        args=[acct.address], account=acct
    )


def _deploy_reserve(acct, verifier):
    return get_contract_factory(contract_file_path=RESERVE).deploy(
        args=[acct.address, acct.address, 100, verifier.address], account=acct
    )


def _make_active_on(reserve, creator, recipient, tranche=1000, interval=0):
    reserve.mint(args=[creator.address, tranche]).transact()
    reserve.create_agreement(args=[recipient.address, tranche]).transact()
    reserve.add_checkpoint(args=["agr_0", CP_URL, CP_CRITERIA, tranche, "once", interval]).transact()
    reserve.finalize_agreement(args=["agr_0"]).transact()
    reserve.connect(recipient).accept_agreement(args=["agr_0"]).transact()
    reserve.reserve_capital(args=["agr_0", tranche]).transact()
    return "agr_0"


def test_verdict_cannot_settle_a_different_reserve():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()

    verifier = _deploy_verifier(acct)
    reserve_a = _deploy_reserve(acct, verifier)
    reserve_b = _deploy_reserve(acct, verifier)

    _make_active_on(reserve_a, acct, bob)
    _make_active_on(reserve_b, acct, bob)

    assert tx_execution_succeeded(verifier.set_reserve(args=[reserve_a.address]).transact())
    verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    case_a = verifier.get_latest_case_for(args=["agr_0", 0]).call()
    assert case_a
    assert verifier.get_verdict(args=[case_a]).call()["reserve"].lower() == reserve_a.address.lower()

    _expect_revert(lambda: reserve_b.apply_verdict(args=[case_a]).transact())
    ag_b = reserve_b.get_agreement(args=["agr_0"]).call()
    assert ag_b["status"] == "active"
    assert ag_b["reserved"] == 1000

    assert tx_execution_succeeded(reserve_a.apply_verdict(args=[case_a]).transact())


def test_epoch_key_is_scoped_per_reserve():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()

    verifier = _deploy_verifier(acct)
    reserve_a = _deploy_reserve(acct, verifier)
    reserve_b = _deploy_reserve(acct, verifier)

    _make_active_on(reserve_a, acct, bob)
    _make_active_on(reserve_b, acct, bob)

    assert tx_execution_succeeded(verifier.set_reserve(args=[reserve_a.address]).transact())
    assert tx_execution_succeeded(
        verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )

    assert tx_execution_succeeded(verifier.set_reserve(args=[reserve_b.address]).transact())
    assert tx_execution_succeeded(
        verifier.run_review(args=["agr_0", 0, SUBMITTER]).transact(transaction_context=_ctx(vf))
    )


# ==================== outcome matrix: state + balance movement ====================

def test_outcome_release_pays_the_full_tranche():
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Release", 100)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "released"
    assert cp["fulfillment_pct"] == 100
    assert cp["released"] == 990
    assert cp["withheld"] == 0

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "completed"
    assert ag["reserved"] == 0
    assert ag["released_total"] == 990
    assert ag["withheld_total"] == 0

    assert _bal(reserve, bob) == 990
    assert _bal(reserve, dave) == 10
    assert _bal(reserve, acct) == 0


def test_outcome_reduce_pays_proportionally_and_withholds_the_rest():
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Reduce", 50)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "reduced"
    assert cp["fulfillment_pct"] == 50
    assert cp["released"] == 495
    assert cp["withheld"] == 500

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "completed"
    assert ag["reserved"] == 0
    assert ag["released_total"] == 495
    assert ag["withheld_total"] == 500

    assert _bal(reserve, bob) == 495
    assert _bal(reserve, dave) == 5
    assert _bal(reserve, acct) == 500


def test_outcome_pause_holds_capital_and_reopens():
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Pause", 0)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "paused"
    assert cp["epoch"] == 2
    assert cp["released"] == 0

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "active"
    assert ag["reserved"] == 1000

    assert _bal(reserve, bob) == 0
    assert _bal(reserve, dave) == 0
    assert _bal(reserve, acct) == 0


def test_outcome_escalate_holds_capital_and_reopens():
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Escalate", 0)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "escalated"
    assert cp["epoch"] == 2
    assert cp["released"] == 0

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "active"
    assert ag["reserved"] == 1000

    assert _bal(reserve, bob) == 0
    assert _bal(reserve, dave) == 0
    assert _bal(reserve, acct) == 0


def test_outcome_cancel_refunds_the_creator():
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Cancel", 0)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "cancelled"
    assert cp["released"] == 0

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "cancelled"
    assert ag["reserved"] == 0

    assert _bal(reserve, bob) == 0
    assert _bal(reserve, dave) == 0
    assert _bal(reserve, acct) == 1000


def test_inconsistent_outcome_does_not_settle():
    """Release claimed at 10% violates the documented Release >= 85 relationship,
    so it must not move capital; the checkpoint reopens instead."""
    acct = get_default_account()
    bob = create_account()
    dave = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_with_fee_wallet(acct, dave)
    _make_active(reserve, acct, bob)

    assert tx_execution_succeeded(_settle(verifier, reserve, vf, _verdict("Release", 10)))

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "pending"
    assert cp["epoch"] == 2
    assert cp["released"] == 0

    ag = reserve.get_agreement(args=["agr_0"]).call()
    assert ag["status"] == "active"
    assert ag["reserved"] == 1000

    assert _bal(reserve, bob) == 0
    assert _bal(reserve, dave) == 0
