import { createClient, createAccount, generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const RESERVE = (process.env.RESERVE_ADDRESS || "").trim();
const VERIFIER = (process.env.VERIFIER_ADDRESS || "").trim();
const POLL_MS = Number(process.env.POLL_INTERVAL_MS || 30000);
const ONCE = process.env.ONCE === "1";

if (!RESERVE || !VERIFIER) {
  console.error("[keeper] set RESERVE_ADDRESS and VERIFIER_ADDRESS");
  process.exit(1);
}

const pk = (process.env.KEEPER_PRIVATE_KEY || generatePrivateKey());
const account = createAccount(pk);

const readClient = createClient({ chain: studionet });
const writeClient = createClient({ chain: studionet, account });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function isBusy(e) {
  const m = String((e && e.message) || e).toLowerCase();
  return m.includes("busy") || m.includes("slots") || m.includes("retry") || m.includes("not supported");
}

async function readContract(address, functionName, args = []) {
  let lastErr;
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      return await readClient.readContract({ address, functionName, args });
    } catch (e) {
      lastErr = e;
      if (isBusy(e)) { await sleep(900 * (attempt + 1)); continue; }
      throw e;
    }
  }
  throw lastErr;
}

async function writeContract(address, functionName, args = [], waitRetries = 30) {
  let hash = null;
  let lastErr;
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      hash = await writeClient.writeContract({ address, functionName, args, value: BigInt(0) });
      break;
    } catch (e) {
      lastErr = e;
      if (isBusy(e)) { await sleep(1200 * (attempt + 1)); continue; }
      throw e;
    }
  }
  if (!hash) throw lastErr;
  await writeClient.waitForTransactionReceipt({ hash, status: "ACCEPTED", interval: 4000, retries: waitRetries });
  return hash;
}

async function tick() {
  const raw = await readContract(RESERVE, "get_due", []);
  const due = typeof raw === "string" ? JSON.parse(raw) : (raw || []);
  const stamp = new Date().toISOString();
  if (!due.length) {
    console.log(`[keeper] ${stamp} nothing due`);
    return;
  }
  console.log(`[keeper] ${stamp} ${due.length} checkpoint(s) due`);
  for (const item of due) {
    const agr = item.agreement_id;
    const idx = Number(item.checkpoint_index);
    try {
      console.log(`[keeper] ${agr}#${idx} -> run_review`);
      await writeContract(VERIFIER, "run_review", [agr, idx, account.address], 120);
      const caseId = await readContract(VERIFIER, "get_latest_case_for", [agr, idx]);
      if (!caseId) {
        console.error(`[keeper] ${agr}#${idx} no case produced, skipping`);
        continue;
      }
      console.log(`[keeper] ${agr}#${idx} -> apply_verdict ${caseId}`);
      await writeContract(RESERVE, "apply_verdict", [caseId], 60);
      console.log(`[keeper] ${agr}#${idx} settled/advanced`);
    } catch (e) {
      console.error(`[keeper] ${agr}#${idx} failed: ${(e && e.message) || e}`);
    }
  }
}

async function main() {
  console.log(`[keeper] keeper address ${account.address}`);
  console.log(`[keeper] reserve ${RESERVE}`);
  console.log(`[keeper] verifier ${VERIFIER}`);
  console.log(`[keeper] mode ${ONCE ? "once" : `loop every ${POLL_MS}ms`}`);
  if (ONCE) {
    await tick();
    return;
  }
  for (;;) {
    try {
      await tick();
    } catch (e) {
      console.error(`[keeper] tick error: ${(e && e.message) || e}`);
    }
    await sleep(POLL_MS);
  }
}

main().catch((e) => {
  console.error("[keeper] fatal:", e);
  process.exit(1);
});
