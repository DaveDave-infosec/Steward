import { getAgreementCount, getAllAgreementIds, getAgreementFull, getVerdictCount } from "./contracts";

async function pool<T, R>(items: T[], limit: number, fn: (x: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const cur = i++;
      results[cur] = await fn(items[cur]);
    }
  }
  const count = Math.min(limit, items.length) || 0;
  await Promise.all(Array.from({ length: count }, () => worker()));
  return results;
}

export async function loadStats(): Promise<{ agreements: number; released: number; verdicts: number }> {
  const agreements = await getAgreementCount();
  const verdicts = await getVerdictCount();
  const ids = (await getAllAgreementIds()).slice(0, 25);
  const loaded = await pool(ids, 4, async (id) => await getAgreementFull(id));
  let released = 0;
  for (const a of loaded as any[]) {
    if (a && a.agreement_id) released += Number(a.released_total || 0);
  }
  return { agreements, released, verdicts };
}
