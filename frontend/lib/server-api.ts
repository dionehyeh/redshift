import { auth } from "@clerk/nextjs/server";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

export async function serverApi<T>(path: string): Promise<T> {
  const { getToken } = auth();
  const token = await getToken();
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody?.error?.message || `Server API failed with status ${res.status}`
    );
  }

  return res.json() as Promise<T>;
}
