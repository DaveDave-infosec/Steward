import { readContract, writeContract } from "./genlayer";

export const RESERVE_ADDRESS = "0xa0858cf642ab3Ff432C135d2dB9a79bA3AE4fa81";
export const VERIFIER_ADDRESS = "0x878daa116D116aa7B8660b3f97fB10349F625b8C";

// ---------- reserve reads ----------
export async function getAllAgreementIds(): Promise<string[]> {
  return (await readContract(RESERVE_ADDRESS, "get_all_agreement_ids", [])) as string[];
}
export async function getAgreementsFor(address: string): Promise<string[]> {
  return (await readContract(RESERVE_ADDRESS, "get_agreements_for", [address])) as string[];
}
export async function getAgreementCount(): Promise<number> {
  return Number(await readContract(RESERVE_ADDRESS, "get_agreement_count", []));
}
export async function getAgreementRaw(agreementId: string): Promise<any> {
  return await readContract(RESERVE_ADDRESS, "get_agreement", [agreementId]);
}
export async function getAgreementFull(agreementId: string): Promise<any> {
  return await readContract(RESERVE_ADDRESS, "get_agreement_full", [agreementId]);
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
export async function runReview(_account: string, agreementId: string, checkpointIndex: number, submitter: string) {
  return writeContract(VERIFIER_ADDRESS, "run_review", [agreementId, checkpointIndex, submitter], 120);
}
export async function getVerdict(caseId: string): Promise<any> {
  return await readContract(VERIFIER_ADDRESS, "get_verdict", [caseId]);
}

// ---------- reserve writes (sender authenticated on-chain; no caller arg) ----------
export async function mint(_account: string, toAddress: string, amount: number) {
  return writeContract(RESERVE_ADDRESS, "mint", [toAddress, amount]);
}
export async function createAgreement(_account: string, recipient: string, maxAllocation: number) {
  return writeContract(RESERVE_ADDRESS, "create_agreement", [recipient, maxAllocation]);
}
export async function addCheckpoint(_account: string, agreementId: string, evidenceUrl: string, criteria: string, trancheAmount: number, reviewCadence: string) {
  return writeContract(RESERVE_ADDRESS, "add_checkpoint", [agreementId, evidenceUrl, criteria, trancheAmount, reviewCadence]);
}
export async function finalizeAgreement(_account: string, agreementId: string) {
  return writeContract(RESERVE_ADDRESS, "finalize_agreement", [agreementId]);
}
export async function acceptAgreement(_account: string, agreementId: string) {
  return writeContract(RESERVE_ADDRESS, "accept_agreement", [agreementId]);
}
export async function reserveCapital(_account: string, agreementId: string, amount: number) {
  return writeContract(RESERVE_ADDRESS, "reserve_capital", [agreementId, amount]);
}
export async function applyVerdict(_account: string, caseId: string) {
  return writeContract(RESERVE_ADDRESS, "apply_verdict", [caseId], 60);
}

export async function cancelAgreement(_account: string, agreementId: string) {
  return writeContract(RESERVE_ADDRESS, "cancel_agreement", [agreementId]);
}
