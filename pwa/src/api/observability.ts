import { pwaAuthHeaders } from "../auth";

export type PwaObservability = {
  generated_at: string;
  window_days: number;
  interactions: { telegram: number; pwa: number };
  llm_errors: { telegram: number; pwa: number };
  mutations_total: number;
  mutations_by_action: { action: string; count: number }[];
  geofence_events: number;
  push_subscriptions_active: number;
  telegram_send_failures: number | null;
  last_interaction_at: { telegram: string | null; pwa: string | null };
};

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE ?? "").trim();
  return raw.replace(/\/$/, "");
}

export async function fetchObservability(days = 7): Promise<PwaObservability> {
  const base = apiBase();
  const url = `${base}/api/pwa/observability/?days=${days}`;
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
    throw new Error(`Falha ao carregar métricas (${res.status}).`);
  }
  return res.json() as Promise<PwaObservability>;
}

export function formatObservabilityWhen(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}