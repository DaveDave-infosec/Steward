# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json


class StewardReserve(gl.Contract):
    owner: str
    fee_wallet: str
    protocol_fee_bps: u256
    verifier_address: str

    balances: TreeMap[str, u256]

    agreement_ids: DynArray[str]
    agreement_counter: u256
    a_creator: TreeMap[str, str]
    a_recipient: TreeMap[str, str]
    a_max_allocation: TreeMap[str, u256]
    a_reserved: TreeMap[str, u256]
    a_released_total: TreeMap[str, u256]
    a_withheld_total: TreeMap[str, u256]
    a_status: TreeMap[str, str]
    a_checkpoint_count: TreeMap[str, u256]
    a_current_index: TreeMap[str, u256]

    c_evidence_url: TreeMap[str, str]
    c_criteria: TreeMap[str, str]
    c_tranche_amount: TreeMap[str, u256]
    c_review_cadence: TreeMap[str, str]
    c_status: TreeMap[str, str]
    c_fulfillment_pct: TreeMap[str, u256]
    c_released: TreeMap[str, u256]
    c_withheld: TreeMap[str, u256]
    c_case_id: TreeMap[str, str]

    def __init__(self, owner_address: str, fee_wallet_address: str, protocol_fee_bps: int, verifier_address: str):
        self.owner = owner_address.lower()
        self.fee_wallet = fee_wallet_address.lower()
        self.protocol_fee_bps = u256(protocol_fee_bps)
        self.verifier_address = verifier_address.lower()
        self.agreement_counter = u256(0)

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower()

    # ---------- token faucet ----------
    @gl.public.write
    def mint(self, to_address: str, amount: int):
        to_address = to_address.lower()
        cur = self.balances[to_address] if to_address in self.balances else u256(0)
        self.balances[to_address] = u256(int(cur) + amount)

    @gl.public.view
    def balance_of(self, address: str) -> int:
        address = address.lower()
        return int(self.balances[address]) if address in self.balances else 0

    @gl.public.view
    def get_config(self) -> dict:
        return {
            "owner": self.owner,
            "fee_wallet": self.fee_wallet,
            "protocol_fee_bps": int(self.protocol_fee_bps),
            "verifier": self.verifier_address,
        }

    # ---------- agreement lifecycle (sender-authenticated) ----------
    @gl.public.write
    def create_agreement(self, recipient: str, max_allocation: int) -> str:
        creator = self._sender()
        agreement_id = "agr_" + str(int(self.agreement_counter))
        self.agreement_counter = u256(int(self.agreement_counter) + 1)
        self.agreement_ids.append(agreement_id)
        self.a_creator[agreement_id] = creator
        self.a_recipient[agreement_id] = recipient.lower()
        self.a_max_allocation[agreement_id] = u256(int(max_allocation))
        self.a_reserved[agreement_id] = u256(0)
        self.a_released_total[agreement_id] = u256(0)
        self.a_withheld_total[agreement_id] = u256(0)
        self.a_status[agreement_id] = "draft"
        self.a_checkpoint_count[agreement_id] = u256(0)
        self.a_current_index[agreement_id] = u256(0)
        return agreement_id

    @gl.public.write
    def add_checkpoint(self, agreement_id: str, evidence_url: str, criteria: str, tranche_amount: int, review_cadence: str):
        if agreement_id not in self.a_status:
            raise gl.UserError("unknown agreement")
        if self.a_status[agreement_id] != "draft":
            raise gl.UserError("agreement locked; checkpoints immutable")
        if self._sender() != self.a_creator[agreement_id]:
            raise gl.UserError("only creator can add checkpoints")
        idx = int(self.a_checkpoint_count[agreement_id])
        ck = agreement_id + "#" + str(idx)
        self.c_evidence_url[ck] = evidence_url
        self.c_criteria[ck] = criteria
        self.c_tranche_amount[ck] = u256(int(tranche_amount))
        self.c_review_cadence[ck] = review_cadence
        self.c_status[ck] = "pending"
        self.c_fulfillment_pct[ck] = u256(0)
        self.c_released[ck] = u256(0)
        self.c_withheld[ck] = u256(0)
        self.c_case_id[ck] = ""
        self.a_checkpoint_count[agreement_id] = u256(idx + 1)

    @gl.public.write
    def finalize_agreement(self, agreement_id: str):
        if agreement_id not in self.a_status:
            raise gl.UserError("unknown agreement")
        if self._sender() != self.a_creator[agreement_id]:
            raise gl.UserError("only creator can finalize")
        if self.a_status[agreement_id] != "draft":
            raise gl.UserError("already finalized")
        if int(self.a_checkpoint_count[agreement_id]) == 0:
            raise gl.UserError("no checkpoints defined")
        self.a_status[agreement_id] = "locked"

    @gl.public.write
    def accept_agreement(self, agreement_id: str):
        if agreement_id not in self.a_status:
            raise gl.UserError("unknown agreement")
        if self.a_status[agreement_id] != "locked":
            raise gl.UserError("agreement not locked for acceptance")
        if self._sender() != self.a_recipient[agreement_id]:
            raise gl.UserError("only the named recipient can accept")
        self.a_status[agreement_id] = "accepted"

    @gl.public.write
    def reserve_capital(self, agreement_id: str, amount: int):
        if agreement_id not in self.a_status:
            raise gl.UserError("unknown agreement")
        if self.a_status[agreement_id] != "accepted":
            raise gl.UserError("agreement must be accepted before reserving")
        creator = self.a_creator[agreement_id]
        if self._sender() != creator:
            raise gl.UserError("only creator can reserve capital")
        amt = int(amount)
        if amt <= 0:
            raise gl.UserError("amount must be positive")
        if amt > int(self.a_max_allocation[agreement_id]):
            raise gl.UserError("exceeds max allocation")
        bal = int(self.balances[creator]) if creator in self.balances else 0
        if bal < amt:
            raise gl.UserError("insufficient GenUSDC balance")
        self.balances[creator] = u256(bal - amt)
        self.a_reserved[agreement_id] = u256(int(self.a_reserved[agreement_id]) + amt)
        self.a_status[agreement_id] = "active"

    # ---------- trustless settlement, bound to the verifier's on-chain verdict ----------
    @gl.public.write
    def apply_verdict(self, case_id: str):
        verifier = gl.get_contract_at(Address(self.verifier_address))
        verdict = verifier.view().get_verdict(case_id)
        if not verdict or "outcome" not in verdict or str(verdict["outcome"]) == "":
            raise gl.UserError("verdict not found on verifier")

        agreement_id = str(verdict["agreement_id"])
        idx = int(verdict["checkpoint_index"])

        if agreement_id not in self.a_status:
            raise gl.UserError("unknown agreement")

        sender = self._sender()
        if sender != self.owner and sender != self.a_creator[agreement_id]:
            raise gl.UserError("only owner or agreement creator can relay verdicts")
        if self.a_status[agreement_id] != "active":
            raise gl.UserError("agreement not active")
        if idx != int(self.a_current_index[agreement_id]):
            raise gl.UserError("not the current checkpoint")

        ck = agreement_id + "#" + str(idx)
        if ck not in self.c_status:
            raise gl.UserError("unknown checkpoint")
        st = self.c_status[ck]
        if st != "pending" and st != "paused" and st != "escalated":
            raise gl.UserError("checkpoint already resolved")

        # the verdict must have been produced against THIS checkpoint's locked inputs
        if str(verdict["evidence_url"]) != self.c_evidence_url[ck]:
            raise gl.UserError("verdict evidence source does not match the locked checkpoint")
        if str(verdict["criteria"]) != self.c_criteria[ck][:400]:
            raise gl.UserError("verdict criteria do not match the locked checkpoint")

        pct = int(verdict["fulfillment_pct"])
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100
        outcome = str(verdict["outcome"])

        creator = self.a_creator[agreement_id]
        recipient = self.a_recipient[agreement_id]
        tranche = int(self.c_tranche_amount[ck])
        reserved = int(self.a_reserved[agreement_id])
        fee_bps = int(self.protocol_fee_bps)

        self.c_fulfillment_pct[ck] = u256(pct)
        self.c_case_id[ck] = case_id

        if outcome == "Pause":
            self.c_status[ck] = "paused"
            return
        if outcome == "Escalate":
            self.c_status[ck] = "escalated"
            return
        if outcome == "Cancel":
            cbal = int(self.balances[creator]) if creator in self.balances else 0
            self.balances[creator] = u256(cbal + reserved)
            self.a_reserved[agreement_id] = u256(0)
            self.c_status[ck] = "cancelled"
            self.a_status[agreement_id] = "cancelled"
            return

        if outcome == "Release":
            frac = 100
        elif outcome == "Reduce":
            frac = pct
        else:
            raise gl.UserError("unknown outcome")

        if tranche > reserved:
            raise gl.UserError("tranche exceeds reserved capital")

        gross = tranche * frac // 100
        fee = gross * fee_bps // 10000
        net = gross - fee
        withheld = tranche - gross

        rbal = int(self.balances[recipient]) if recipient in self.balances else 0
        self.balances[recipient] = u256(rbal + net)
        if fee > 0:
            fbal = int(self.balances[self.fee_wallet]) if self.fee_wallet in self.balances else 0
            self.balances[self.fee_wallet] = u256(fbal + fee)
        if withheld > 0:
            cbal = int(self.balances[creator]) if creator in self.balances else 0
            self.balances[creator] = u256(cbal + withheld)

        self.a_reserved[agreement_id] = u256(reserved - tranche)
        self.a_released_total[agreement_id] = u256(int(self.a_released_total[agreement_id]) + net)
        self.a_withheld_total[agreement_id] = u256(int(self.a_withheld_total[agreement_id]) + withheld)
        self.c_released[ck] = u256(net)
        self.c_withheld[ck] = u256(withheld)
        self.c_status[ck] = "released" if outcome == "Release" else "reduced"

        nxt = idx + 1
        self.a_current_index[agreement_id] = u256(nxt)
        if nxt >= int(self.a_checkpoint_count[agreement_id]):
            self.a_status[agreement_id] = "completed"

    # ---------- views ----------
    @gl.public.view
    def get_agreement(self, agreement_id: str) -> dict:
        if agreement_id not in self.a_status:
            return {}
        return {
            "agreement_id": agreement_id,
            "creator": self.a_creator[agreement_id],
            "recipient": self.a_recipient[agreement_id],
            "max_allocation": int(self.a_max_allocation[agreement_id]),
            "reserved": int(self.a_reserved[agreement_id]),
            "released_total": int(self.a_released_total[agreement_id]),
            "withheld_total": int(self.a_withheld_total[agreement_id]),
            "status": self.a_status[agreement_id],
            "checkpoint_count": int(self.a_checkpoint_count[agreement_id]),
            "current_index": int(self.a_current_index[agreement_id]),
        }

    @gl.public.view
    def get_checkpoint(self, agreement_id: str, index: int) -> dict:
        ck = agreement_id + "#" + str(int(index))
        if ck not in self.c_status:
            return {}
        return {
            "agreement_id": agreement_id,
            "index": int(index),
            "evidence_url": self.c_evidence_url[ck],
            "criteria": self.c_criteria[ck],
            "tranche_amount": int(self.c_tranche_amount[ck]),
            "review_cadence": self.c_review_cadence[ck],
            "status": self.c_status[ck],
            "fulfillment_pct": int(self.c_fulfillment_pct[ck]),
            "released": int(self.c_released[ck]),
            "withheld": int(self.c_withheld[ck]),
            "case_id": self.c_case_id[ck],
        }

    @gl.public.view
    def get_agreement_full(self, agreement_id: str) -> dict:
        if agreement_id not in self.a_status:
            return {}
        count = int(self.a_checkpoint_count[agreement_id])
        cps = []
        for i in range(count):
            ck = agreement_id + "#" + str(i)
            cps.append({
                "index": i,
                "evidence_url": self.c_evidence_url[ck],
                "criteria": self.c_criteria[ck],
                "tranche_amount": int(self.c_tranche_amount[ck]),
                "status": self.c_status[ck],
                "fulfillment_pct": int(self.c_fulfillment_pct[ck]),
                "released": int(self.c_released[ck]),
                "withheld": int(self.c_withheld[ck]),
                "case_id": self.c_case_id[ck],
            })
        return {
            "agreement_id": agreement_id,
            "creator": self.a_creator[agreement_id],
            "recipient": self.a_recipient[agreement_id],
            "status": self.a_status[agreement_id],
            "max_allocation": int(self.a_max_allocation[agreement_id]),
            "reserved": int(self.a_reserved[agreement_id]),
            "released_total": int(self.a_released_total[agreement_id]),
            "withheld_total": int(self.a_withheld_total[agreement_id]),
            "checkpoint_count": count,
            "current_index": int(self.a_current_index[agreement_id]),
            "checkpoints_json": json.dumps(cps),
        }

    @gl.public.view
    def get_agreements_for(self, address: str) -> list:
        addr = address.lower()
        out = []
        for i in range(len(self.agreement_ids) - 1, -1, -1):
            aid = self.agreement_ids[i]
            if self.a_creator[aid] == addr or self.a_recipient[aid] == addr:
                out.append(aid)
        return out

    @gl.public.view
    def get_agreement_count(self) -> int:
        return int(self.agreement_counter)

    @gl.public.view
    def get_all_agreement_ids(self) -> list:
        out = []
        for i in range(len(self.agreement_ids) - 1, -1, -1):
            out.append(self.agreement_ids[i])
        return out
