export function getMine(address: string): string[] {
  try {
    const raw = localStorage.getItem("steward_mine_" + address.toLowerCase());
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function addMine(address: string, id: string) {
  try {
    const cur = getMine(address);
    if (!cur.includes(id)) {
      cur.push(id);
      localStorage.setItem("steward_mine_" + address.toLowerCase(), JSON.stringify(cur));
    }
  } catch {
    /* ignore */
  }
}
