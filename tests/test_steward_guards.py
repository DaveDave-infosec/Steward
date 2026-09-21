"""
Steward V3 guard + keeper-due tests — the REAL two-contract flow on glsim.

Guard tests (V2.1, unchanged behaviour): premature reviews refused, one verdict
per epoch, permissionless settlement, malformed-first-case recovery, stale-epoch
rejection.

Keeper-due tests (V3): the get_due() surface and the next_review_at backoff that
an off-chain keeper polls. Time is the contract's deterministic transaction
timestamp; we avoid view-time-warp by contrasting interval=0 (due) with a huge
interval (backoff removes it from due), proving the next_review_at gate.

No skips, no copied logic.

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


def _review(verifier, vf, idx=0):
    verifier.run_review(args=["agr_0", idx, SUBMITTER]).transact(transaction_context=_ctx(vf))
    return verifier.get_latest_case_for(args=["agr_0", idx]).call()


def _due_ids(reserve):
    return [d["agreement_id"] for d in json.loads(reserve.get_due(args=[]).call())]


# ============================ guard tests (V2.1) ============================

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


# ============================ keeper-due tests (V3) ============================

def test_active_checkpoint_is_due():
    acct = get_default_account()
    bob = create_account()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob, interval=0)

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


def test_backoff_removes_checkpoint_from_due():
    acct = get_default_account()
    bob = create_account()
    vf = get_validator_factory()
    verifier, reserve = _deploy_pair(acct)
    _make_active(reserve, acct, bob, interval=BIG_INTERVAL)

    assert "agr_0" in _due_ids(reserve)

    v_bad = _review(verifier, vf)
    assert tx_execution_succeeded(reserve.apply_verdict(args=[v_bad]).transact())

    cp = reserve.get_checkpoint(args=["agr_0", 0]).call()
    assert cp["status"] == "pending"
    assert cp["next_review_at"] > 0
    assert "agr_0" not in _due_ids(reserve)
