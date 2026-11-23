import { pwaAuthHeaders } from "../auth";

function apiBase(): string {
  const fromEnv = import.meta.env.VITE_DEV_API as string | undefined;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export type GeofenceEventRow = {
  id: number;
  location_label: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  items_count: number;
  telegram_sent: boolean;
  created_at: string;
};

export async function fetchGeofenceEvents(limit = 40): Promise<GeofenceEventRow[]> {
  const base = apiBase();
  const res = await fetch(`${base}/api/pwa/geofence/events/?limit=${limit}`, {
    headers: { Accept: "application/json", ...pwaAuthHeaders() },
  });
  if (res.status === 401) throw new Error("Token inválido.");
  if (!res.ok) throw new Error("Falha ao carregar alertas.");
  return res.json();
}