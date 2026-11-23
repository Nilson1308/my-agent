import { pwaAuthHeaders } from "../auth";

export type ShoppingItemRow = { id: number; name: string; quantity: string };
export type TaskRow = {
  id: number;
  title: string;
  context: string;
  due_date: string | null;
  due_at: string | null;
};
export type EventRow = {
  id: number;
  title: string;
  context: string;
  start_at: string;
};

export type PwaSnapshot = {
  generated_at: string;
  shopping: {
    count: number;
    text: string;
    items: ShoppingItemRow[];
  };
  tasks_pending: TaskRow[];
  events_today: EventRow[];
};

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE ?? "").trim();
  return raw.replace(/\/$/, "");
}

export async function fetchSnapshot(): Promise<PwaSnapshot> {
  const base = apiBase();
  const url = `${base}/api/pwa/snapshot/`;
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
      ...pwaAuthHeaders(),
    },
  });
  if (res.status === 401) {
    throw new Error("Token inválido ou ausente.");
  }
  if (!res.ok) {
    throw new Error(`Falha ao carregar (${res.status}).`);
  }
  return res.json() as Promise<PwaSnapshot>;
}

export function formatGeneratedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso.includes("T") ? iso : `${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}