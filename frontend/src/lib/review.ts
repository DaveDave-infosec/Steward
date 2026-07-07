import { getVerdictCount, runReview, getVerdict, applyVerdict, getCheckpointRaw } from "./contracts";

export async function executeReview(
  account: string,
  agreementId: string,
  checkpointIndex: number,
  evidenceUrl: string,
  criteria: string,
  onPhase?: (msg: string) => void,
): Promise<any> {
  onPhase?.("Reading locked evidence source…");
  const countBefore = await getVerdictCount();
  const caseId = "steward_" + countBefore;

  onPhase?.("Validators fetching evidence & judging substance (consensus forming)…");
  await runReview(account, agreementId, checkpointIndex, evidenceUrl, criteria, account);

  onPhase?.("Reading verdict…");
  let v = await getVerdict(caseId);
  let tries = 0;
  while ((!v || !v.outcome) && tries < 10) {
    await new Promise((r) => setTimeout(r, 2500));
    v = await getVerdict(caseId);
    tries++;
  }
  if (!v || !v.outcome) throw new Error("Verdict not readable yet for " + caseId);
  const pct = Number(v.fulfillment_pct);

  onPhase?.("Standing order executes: " + v.outcome + " at " + pct + "%…");
  await applyVerdict(account, agreementId, checkpointIndex, pct, v.outcome, caseId);

  let cp = await getCheckpointRaw(agreementId, checkpointIndex);
  let t2 = 0;
  while (cp && cp.status === "pending" && t2 < 12) {
    await new Promise((r) => setTimeout(r, 2500));
    cp = await getCheckpointRaw(agreementId, checkpointIndex);
    t2++;
  }
  return v;
}
