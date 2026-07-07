import { readContract, writeContract } from "./genlayer";

export const RESERVE_ADDRESS = "0x610F1D7dD5920499E06f8E1a82fe459E2B793dd3";
export const VERIFIER_ADDRESS = "0x1e4Eba962BFF2b118Bc19d8d5304de92f927b622";

// ---------- reserve reads ----------
export async function getAllAgreementIds(): Promise<string[]> {
  return (await readContract(RESERVE_ADDRESS, "get_all_agreement_ids", [])) as string[];
}
export async function getAgreementsFor(address: string): Promise<string[]> {
  return (await readContract(RESERVE_ADDRESS, "get_agreements_for", [address])) as string[];
}
export async function getAgreementFull(agreementId: string): Promise<any> {
  return await readContract(RESERVE_ADDRESS, "get_agreement_full", [agreementId]);
}
export async function getAgreementCount(): Promise<number> {
  return Number(await readContract(RESERVE_ADDRESS, "get_agreement_count", []));
}
export async function getAgreementRaw(agreementId: string): Promise<any> {
  return await readContract(RESERVE_ADDRESS, "get_agreement", [agreementId]);
}
export async function getCheckpointRaw(agreementId: string, index: number): Promise<any> {
  return await readContract(RESERVE_ADDRESS, "get_checkpoint", [agreementId, index]);
}
export async function balanceOf(address: string): Promise<number> {
  return Number(await readContract(RESERVE_ADDRESS, "balance_of", [address]));
}

// ---------- verifier ----------
export async function getVerdictCount(): Promise<number> {
  return Number(await readContract(VERIFIER_ADDRESS, "get_verdict_count", []));
}
export async function runReview(_account: string, agreementId: string, checkpointIndex: number, evidenceUrl: string, criteria: string, submitter: string) {
  return writeContract(VERIFIER_ADDRESS, "run_review", [agreementId, checkpointIndex, evidenceUrl, criteria, submitter], 120);
}
export async function getVerdict(caseId: string): Promise<any> {
  return await readContract(VERIFIER_ADDRESS, "get_verdict", [caseId]);
}

// ---------- reserve writes ----------
export async function mint(_account: string, toAddress: string, amount: number) {
  return writeContract(RESERVE_ADDRESS, "mint", [toAddress, amount]);
}
export async function createAgreement(account: string, recipient: string, maxAllocation: number) {
  return writeContract(RESERVE_ADDRESS, "create_agreement", [account, recipient, maxAllocation]);
}
export async function addCheckpoint(account: string, agreementId: string, evidenceUrl: string, criteria: string, trancheAmount: number, reviewCadence: string) {
  return writeContract(RESERVE_ADDRESS, "add_checkpoint", [account, agreementId, evidenceUrl, criteria, trancheAmount, reviewCadence]);
}
export async function finalizeAgreement(account: string, agreementId: string) {
  return writeContract(RESERVE_ADDRESS, "finalize_agreement", [account, agreementId]);
}
export async function acceptAgreement(account: string, agreementId: string) {
  return writeContract(RESERVE_ADDRESS, "accept_agreement", [account, agreementId]);
}
export async function reserveCapital(account: string, agreementId: string, amount: number) {
  return writeContract(RESERVE_ADDRESS, "reserve_capital", [account, agreementId, amount]);
}
export async function applyVerdict(account: string, agreementId: string, checkpointIndex: number, fulfillmentPct: number, outcome: string, caseId: string) {
  return writeContract(RESERVE_ADDRESS, "apply_verdict", [account, agreementId, checkpointIndex, fulfillmentPct, outcome, caseId], 60);
}
