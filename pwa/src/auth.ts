const STORAGE_KEY = "my_agent_pwa_token";

export function getPwaToken(): string {
  return sessionStorage.getItem(STORAGE_KEY) ?? "";
}

export function setPwaToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEY, token.trim());
}

export function clearPwaToken(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function pwaAuthHeaders(): HeadersInit {
  const token = getPwaToken();
  if (!token) return {};
  return { "X-PWA-Token": token };
}