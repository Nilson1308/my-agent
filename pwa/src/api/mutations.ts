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

async function patchTaskStatus(taskId: number, status: "done" | "pending"): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/tasks/${taskId}/`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ status }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}

export async function completeTask(taskId: number): Promise<void> {
  return patchTaskStatus(taskId, "done");
}

export async function reopenTask(taskId: number): Promise<void> {
  return patchTaskStatus(taskId, "pending");
}

export async function createShoppingItem(
  name: string,
  quantity = ""
): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/shopping/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ name: name.trim(), quantity: quantity.trim() }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}

export async function createTask(title: string, context: string): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/tasks/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ title: title.trim(), context }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (!res.ok) throw new Error(await parseError(res));
}

export async function snoozeEvent(
  eventId: number,
  opts: { minutes?: number; preset?: "tomorrow_morning" }
): Promise<void> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/events/${eventId}/snooze/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify(opts),
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