// Server-side API helper — calls the FastAPI backend directly (no browser)
import { auth } from "@clerk/nextjs/server";
import { ApiError } from "@/lib/api";

const API = process.env.API_BASE_URL || "http://localhost:8000";

export async function serverApi<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { getToken } = auth();
  const token = await getToken();

  const res = await fetch(`${API}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers as Record<string, string> | undefined),
    },
    cache: "no-store",
  });

  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = data as {
      error?: { code?: string; message?: string };
      detail?: string;
    };
    throw new ApiError(
      error.error?.message || error.detail || `API error ${res.status} on ${path}`,
      res.status,
      error.error?.code || "REQUEST_FAILED",
    );
  }
  return data as T;
}
