import { pwaAuthHeaders } from "./auth";

function apiBase(): string {
  const fromEnv = import.meta.env.VITE_DEV_API as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

export async function subscribeMyAgentPush(): Promise<string> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("Push não suportado neste navegador.");
  }

  const base = apiBase();
  const cfg = await fetch(`${base}/api/pwa/push/vapid/`).then((r) => r.json());
  if (!cfg.enabled || !cfg.public_key) {
    throw new Error("Push não configurado no servidor (VAPID).");
  }

  const perm = await Notification.requestPermission();
  if (perm !== "granted") throw new Error("Permissão de notificação negada.");

  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(cfg.public_key),
    });
  }

  const json = sub.toJSON();
  const res = await fetch(`${base}/api/pwa/push/subscribe/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...pwaAuthHeaders(),
    },
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: json.keys,
      user_agent: navigator.userAgent,
    }),
  });
  if (res.status === 401) throw new Error("Token inválido — entre novamente.");
  if (!res.ok) throw new Error("Falha ao registrar push.");
  return "Lembretes e compromissos neste aparelho.";
}