import { pwaAuthHeaders } from "../auth";

function apiBase(): string {
  const fromEnv = import.meta.env.VITE_DEV_API as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export type ChatResponse = {
  reply: string;
  llm_outcome: string;
  interaction_log_id: number | null;
  pending_confirmation: boolean;
};

async function parseError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string };
    if (data.detail) return data.detail;
  } catch {
    /* ignore */
  }
  return `Erro ${res.status}`;
}

export async function sendChatAudio(
  blob: Blob | File,
  filename = "voice.webm",
): Promise<ChatResponse> {
  const base = apiBase();
  const form = new FormData();
  const name = blob instanceof File && blob.name ? blob.name : filename;
  form.append("audio", blob, name);
  const res = await fetch(`${base}/api/pwa/chat/audio/`, {
    method: "POST",
    headers: { Accept: "application/json", ...pwaAuthHeaders() },
    body: form,
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (res.status === 429) throw new Error("Muitas mensagens; aguarde um minuto.");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ChatResponse>;
}

export async function sendChatMessage(text: string): Promise<ChatResponse> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/chat/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({ text }),
  });
  if (res.status === 401) throw new Error("Token inválido ou ausente.");
  if (res.status === 429) throw new Error("Muitas mensagens; aguarde um minuto.");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ChatResponse>;
}