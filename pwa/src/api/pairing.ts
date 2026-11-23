import { pwaAuthHeaders } from "../auth";

function apiBase(): string {
  const fromEnv = import.meta.env.VITE_DEV_API as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export async function exchangePairingCode(code: string): Promise<string> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/pairing/exchange/`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ code: code.trim() }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: string }).detail;
    throw new Error(detail || "Código inválido ou expirado.");
  }
  const data = (await res.json()) as { token: string };
  return data.token;
}

export async function createPairingLink(): Promise<{
  code: string;
  expires_in: number;
  pair_url: string;
}> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/pairing/create/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
  });
  if (!res.ok) throw new Error("Falha ao gerar código de pairing.");
  return res.json();
}