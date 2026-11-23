import { pwaAuthHeaders } from "../auth";

function apiBase(): string {
  const fromEnv = import.meta.env.VITE_DEV_API as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export type PdfIngestResult = {
  filename: string;
  chunks: number;
  chars: number;
  note_ids: number[];
  truncated: boolean;
  context: string;
};

export async function uploadPdf(
  file: File,
  context = "pessoal"
): Promise<PdfIngestResult> {
  const base = apiBase();
  const form = new FormData();
  form.append("file", file, file.name);
  form.append("context", context);
  const res = await fetch(`${base}/api/pwa/documents/pdf/`, {
    method: "POST",
    headers: { Accept: "application/json", ...pwaAuthHeaders() },
    body: form,
  });
  if (res.status === 401) throw new Error("Token inválido.");
  if (res.status === 429) throw new Error("Muitos envios; aguarde um minuto.");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Falha ao enviar PDF.");
  }
  return res.json();
}