import { auth } from "@clerk/nextjs/server";
import { getMockResponse } from "./mock-data";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

export async function serverApi<T>(path: string): Promise<T> {
  let token: string | null = null;
  try {
    const authSession = await auth();
    token = await authSession.getToken();
  } catch {
    token = null;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    });

    if (res.ok) {
      return (await res.json()) as T;
    }
  } catch {
    // When backend is not running during frontend development, seamlessly return mock data
    const mock = getMockResponse<T>(path);
    if (mock !== null) {
      return mock;
    }
  }

  const mockFallback = getMockResponse<T>(path);
  if (mockFallback !== null) {
    return mockFallback;
  }

  throw new Error(`Server API request failed for ${path}`);
}
