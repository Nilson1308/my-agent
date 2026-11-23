import { pwaAuthHeaders } from "../auth";

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE ?? "").trim();
  return raw.replace(/\/$/, "");
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    /* ignore */
  }
  return `Erro (${res.status})`;
}

export async function patchShoppingBought(
  itemId: number,
  bought: boolean
): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/shopping/${itemId}/`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ bought }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}

export async function markShoppingBought(itemId: number): Promise<void> {
  return patchShoppingBought(itemId, true);
}

export async function unmarkShoppingBought(itemId: number): Promise<void> {
  return patchShoppingBought(itemId, false);
}

export async function completeTask(taskId: number): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/tasks/${taskId}/`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      ...pwaAuthHeaders(),
    },
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}

export async function dismissEvent(eventId: number): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/events/${eventId}/`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ dismissed: true }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}