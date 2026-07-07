import { createClient, createAccount, generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

export const STEWARD_CHAIN = studionet;
export const CHAIN_ID = 61999 as const;

export function normAddr(a: string): string {
  return a.toLowerCase();
}

type Mode = "metamask" | "demo";
let mode: Mode = "demo";
let mmAddress: string | null = null;
let mmProvider: any = null;
let burnerAccount: any = null;

export function setWalletProvider(p: any) {
  mmProvider = p;
}

function getBurner() {
  if (!burnerAccount) {
    let pk = localStorage.getItem("steward_burner_pk");
    if (!pk) {
      pk = generatePrivateKey();
      localStorage.setItem("steward_burner_pk", pk);
    }
    burnerAccount = createAccount(pk as `0x${string}`);
  }
  return burnerAccount;
}

export function resetBurner() {
  burnerAccount = null;
  try {
    localStorage.removeItem("steward_burner_pk");
  } catch {
    /* ignore */
  }
}

export function activateDemo(): string {
  mode = "demo";
  return (getBurner().address as string).toLowerCase();
}

export function activateMetaMask(address: string) {
  mode = "metamask";
  mmAddress = address.toLowerCase();
}

function applyProvider() {
  if (mmProvider) {
    try {
      (window as any).ethereum = mmProvider;
    } catch {
      /* provider not reassignable */
    }
  }
}

function getReadClient() {
  return createClient({ chain: studionet }) as any;
}

async function getWriteClient() {
  if (mode === "demo") {
    return createClient({ chain: studionet, account: getBurner() }) as any;
  }
  applyProvider();
  const client = createClient({ chain: studionet, account: mmAddress as `0x${string}` }) as any;
  await client.connect("studionet");
  return client;
}

function isBusy(e: any): boolean {
  const m = String((e && e.message) || e).toLowerCase();
  return m.includes("busy") || m.includes("slots") || m.includes("retry") || m.includes("not supported");
}

export async function readContract(address: string, functionName: string, args: unknown[] = []) {
  const client = getReadClient();
  let lastErr: any;
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      return await client.readContract({ address, functionName, args });
    } catch (e: any) {
      lastErr = e;
      if (isBusy(e)) {
        await new Promise((r) => setTimeout(r, 900 * (attempt + 1)));
        continue;
      }
      throw e;
    }
  }
  throw lastErr;
}

export async function writeContract(address: string, functionName: string, args: unknown[] = [], waitRetries = 30) {
  const client = await getWriteClient();
  let hash: string | null = null;
  let lastErr: any;
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      hash = await client.writeContract({ address, functionName, args, value: BigInt(0) });
      break;
    } catch (e: any) {
      lastErr = e;
      if (isBusy(e)) {
        await new Promise((r) => setTimeout(r, 1200 * (attempt + 1)));
        continue;
      }
      throw e;
    }
  }
  if (!hash) throw lastErr;
  await client.waitForTransactionReceipt({ hash: hash as any, status: "ACCEPTED", interval: 4000, retries: waitRetries });
  return hash as string;
}
