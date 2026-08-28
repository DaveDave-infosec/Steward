# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json
import re


@allow_storage
class StewardVerifier(gl.Contract):
    owner: str
    reserve_address: str
    verdict_ids: DynArray[str]
    verdict_counter: u256
    v_agreement_id: TreeMap[str, str]
    v_checkpoint_index: TreeMap[str, u256]
    v_evidence_url: TreeMap[str, str]
    v_criteria: TreeMap[str, str]
    v_fulfillment_pct: TreeMap[str, u256]
    v_outcome: TreeMap[str, str]
    v_reasoning: TreeMap[str, str]
    v_minority_note: TreeMap[str, str]
    v_evidence_excerpt: TreeMap[str, str]
    v_submitter: TreeMap[str, str]
    v_parsed_ok: TreeMap[str, str]
    v_epoch: TreeMap[str, u256]
    v_epoch_used: TreeMap[str, str]

    def __init__(self, owner_address: str):
        self.owner = owner_address.lower()
        self.reserve_address = ""
        self.verdict_counter = u256(0)

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower()

    @gl.public.write
    def set_reserve(self, reserve_address: str):
        if self._sender() != self.owner:
            raise Exception("only owner can set reserve")
        self.reserve_address = reserve_address.lower()

    @gl.public.view
    def get_reserve(self) -> str:
        return self.reserve_address

    @gl.public.write
    def run_review(
        self,
        agreement_id: str,
        checkpoint_index: int,
        submitter: str,
    ) -> str:
        case_id = "steward_" + str(int(self.verdict_counter))
        # pull canonical state directly from the reserve (the vault); no caller may
        # supply evidence or criteria to a review.
        if self.reserve_address == "":
            raise Exception("reserve address not configured")
        reserve = gl.get_contract_at(Address(self.reserve_address))

        # reviews are only possible for the ACTIVE, CURRENT checkpoint.
        ag = reserve.view().get_agreement(agreement_id)
        if not ag or "status" not in ag or str(ag["status"]) == "":
            raise Exception("unknown agreement on reserve")
        if str(ag["status"]) != "active":
            raise Exception("agreement is not active")
        if int(ag["current_index"]) != int(checkpoint_index):
            raise Exception("not the current checkpoint")

        cp = reserve.view().get_checkpoint(agreement_id, checkpoint_index)
        if not cp or "evidence_url" not in cp or str(cp["evidence_url"]) == "":
            raise Exception("unknown checkpoint on reserve")
        local_url = str(cp["evidence_url"])
        local_criteria = str(cp["criteria"])
        epoch = int(cp["epoch"])

        # one verdict per review epoch: a fresh review requires a fresh epoch, so a
        # verdict cannot be re-rolled inside the same epoch.
        epoch_key = agreement_id + "#" + str(int(checkpoint_index)) + "#" + str(epoch)
        if epoch_key in self.v_epoch_used:
            raise Exception("a verdict already exists for this review epoch")

        def fetch_evidence() -> str:
            response = gl.nondet.web.get(local_url)
            body = response.body.decode("utf-8")
            return body[:3000]

        evidence = gl.eq_principle.strict_eq(fetch_evidence)
        local_evidence = evidence

        def get_input() -> str:
            return (
                "EVIDENCE (fetched from locked source " + local_url + "):\n"
                + local_evidence
                + "\n\nLOCKED CRITERIA:\n" + local_criteria
            )

        task = (
            "You are a verifier for a software development grant milestone. Judge "
            "ONLY from the EVIDENCE whether the delivered work satisfies the LOCKED "
            "CRITERIA, and assign a fulfillment percentage from 0 to 100.\n"
            "SCORING RULES:\n"
            "- If the criterion lists several independent requirements (e.g. 'A and "
            "B'), score PROPORTIONALLY: fulfillment_pct is roughly the share of "
            "those requirements the evidence genuinely supports. Meeting one of two "
            "is about 50, not 0.\n"
            "- Distinguish claims from proof. For a requirement about what the "
            "project DOCUMENTS or DESCRIBES, the documented text in the evidence IS "
            "valid proof. For a requirement that something is IMPLEMENTED, DEPLOYED, "
            "TAGGED, RELEASED, or LIVE, require a concrete artifact in the evidence "
            "(a file listing, a tag entry, a contract address, a reachable "
            "endpoint); a bare description is partial support, not full proof.\n"
            "- Reward genuine substance; never reward padding (empty commits, files "
            "present but not implementing the requirement, or evidence about "
            "something other than what the criterion asks).\n"
            "OUTCOME (choose one, consistent with fulfillment_pct):\n"
            "- Release  : fulfillment_pct >= 85.\n"
            "- Reduce   : 15 <= fulfillment_pct < 85 (partially met; released "
            "proportionally).\n"
            "- Pause    : evidence unreachable, empty, or too thin to judge yet.\n"
            "- Escalate : evidence genuinely contradictory/ambiguous, needs a DAO "
            "decision.\n"
            "- Cancel   : fulfillment_pct is ~0 AND the requirement is clearly not "
            "met or the submission looks like a gaming attempt (wrong source, "
            "fabricated claim, total absence of the required artifact).\n"
            "Return ONLY one JSON object with keys: fulfillment_pct (integer "
            "0-100), outcome (one of Release, Reduce, Pause, Escalate, Cancel), "
            "reasoning (1-3 sentences grounded in the evidence), minority_note "
            "(one sentence with the strongest dissenting view, or empty string)."
        )
        criteria_check = (
            "The response is exactly one valid JSON object. fulfillment_pct is an "
            "integer 0-100. outcome is one of Release, Reduce, Pause, Escalate, "
            "Cancel and is consistent with the thresholds (Release>=85, Reduce "
            "15-84, Cancel near 0). reasoning is a non-empty string grounded in the "
            "actual evidence. A multi-part criterion that is partly satisfied is "
            "scored proportionally, not as zero."
        )

        raw = gl.eq_principle.prompt_non_comparative(
            get_input,
            task=task,
            criteria=criteria_check,
        )

        pct = 0
        outcome = ""
        reasoning = ""
        minority = ""
        parsed_ok = "no"
        try:
            first = raw.find("{")
            last = raw.rfind("}")
            cleaned = raw[first:last + 1]
            cleaned = re.sub(r",(?!\s*?[\{\[\"'\w])", "", cleaned)
            data = json.loads(cleaned)
            pct = int(data.get("fulfillment_pct", 0))
            outcome = str(data.get("outcome", ""))
            reasoning = str(data.get("reasoning", ""))
            minority = str(data.get("minority_note", ""))
            parsed_ok = "yes"
        except Exception:
            parsed_ok = "no"

        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

        self.verdict_ids.append(case_id)
        self.verdict_counter = u256(int(self.verdict_counter) + 1)
        self.v_agreement_id[case_id] = agreement_id
        self.v_checkpoint_index[case_id] = u256(int(checkpoint_index))
        self.v_evidence_url[case_id] = local_url
        self.v_criteria[case_id] = local_criteria
        self.v_fulfillment_pct[case_id] = u256(pct)
        self.v_outcome[case_id] = outcome
        self.v_reasoning[case_id] = reasoning[:400]
        self.v_minority_note[case_id] = minority[:300]
        self.v_evidence_excerpt[case_id] = local_evidence[:400]
        self.v_submitter[case_id] = submitter.lower()
        self.v_parsed_ok[case_id] = parsed_ok
        self.v_epoch[case_id] = u256(epoch)
        self.v_epoch_used[epoch_key] = case_id
        return case_id

    @gl.public.view
    def get_verdict(self, case_id: str) -> dict:
        if case_id not in self.v_outcome:
            return {}
        return {
            "case_id": case_id,
            "agreement_id": self.v_agreement_id[case_id],
            "checkpoint_index": int(self.v_checkpoint_index[case_id]),
            "evidence_url": self.v_evidence_url[case_id],
            "criteria": self.v_criteria[case_id],
            "fulfillment_pct": int(self.v_fulfillment_pct[case_id]),
            "outcome": self.v_outcome[case_id],
            "reasoning": self.v_reasoning[case_id],
            "minority_note": self.v_minority_note[case_id],
            "evidence_excerpt": self.v_evidence_excerpt[case_id],
            "submitter": self.v_submitter[case_id],
            "parsed_ok": self.v_parsed_ok[case_id],
            "epoch": int(self.v_epoch[case_id]) if case_id in self.v_epoch else 0,
        }

    @gl.public.view
    def get_latest_case_for(self, agreement_id: str, checkpoint_index: int) -> str:
        idx = int(checkpoint_index)
        for i in range(len(self.verdict_ids) - 1, -1, -1):
            cid = self.verdict_ids[i]
            if self.v_agreement_id[cid] == agreement_id and int(self.v_checkpoint_index[cid]) == idx:
                return cid
        return ""

    @gl.public.view
    def get_verdict_count(self) -> int:
        return int(self.verdict_counter)

    @gl.public.view
    def get_all_verdict_ids(self) -> list:
        out = []
        for i in range(len(self.verdict_ids) - 1, -1, -1):
            out.append(self.verdict_ids[i])
        return out
