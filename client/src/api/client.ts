/** Base fetch wrapper. All paths are relative to VITE_API_SERVER_URL. */
const BASE = (import.meta.env.VITE_API_SERVER_URL as string | undefined) ?? 'http://localhost:8000';

export async function api<T>(
  path: string,
  init?: RequestInit,
  token?: string,
): Promise<T> {
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
      ...init?.headers,
    },
    ...init,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json() as { detail?: string };
      if (body.detail) detail = String(body.detail);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  // 204 / empty body
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}
