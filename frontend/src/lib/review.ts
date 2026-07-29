import { getVerdictCount, runReview, getVerdict, applyVerdict, getCheckpointRaw } from "./contracts";

export async function executeReview(
  account: string,
  agreementId: string,
  checkpointIndex: number,
  onPhase?: (msg: string) => void,
): Promise<any> {
  onPhase?.("Reading the locked checkpoint from the vault…");
  const countBefore = await getVerdictCount();
  const caseId = "steward_" + countBefore;

  onPhase?.("Validators fetching evidence & judging substance (consensus forming)…");
  await runReview(account, agreementId, checkpointIndex, account);

  onPhase?.("Reading verdict…");
  let v = await getVerdict(caseId);
  let tries = 0;
  while ((!v || !v.outcome) && tries < 10) {
    await new Promise((r) => setTimeout(r, 2500));
    v = await getVerdict(caseId);
    tries++;
  }
  if (!v || !v.outcome) throw new Error("Verdict not readable yet for " + caseId);

  onPhase?.("Reserve reads the verifier verdict on-chain & settles by consensus…");
  await applyVerdict(account, caseId);

  let cp = await getCheckpointRaw(agreementId, checkpointIndex);
  let t2 = 0;
  while (cp && cp.status === "pending" && t2 < 12) {
    await new Promise((r) => setTimeout(r, 2500));
    cp = await getCheckpointRaw(agreementId, checkpointIndex);
    t2++;
  }
  return v;
}
