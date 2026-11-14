import { getMockResponse } from "./mock-data";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.API_BASE_URL ||
  "http://localhost:8000";

/**
 * Direct client-to-FastAPI fetch client with development mock fallback.
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token: string | null = null;
  if (typeof window !== "undefined" && (window as any).Clerk?.session) {
    try {
      token = await (window as any).Clerk.session.getToken();
    } catch {
      token = null;
    }
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const targetUrl = `${API_BASE}/api/v1${normalizedPath}`;

  try {
    const res = await fetch(targetUrl, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });

    if (res.ok) {
      return (await res.json()) as T;
    }
  } catch {
    // When backend is not running during frontend development, seamlessly return mock data
    const mock = getMockResponse<T>(normalizedPath);
    if (mock !== null) {
      return mock;
    }
  }

  const mockFallback = getMockResponse<T>(normalizedPath);
  if (mockFallback !== null) {
    return mockFallback;
  }

  throw new ApiError(500, "DATA_UNAVAILABLE", `Failed to fetch ${normalizedPath}`);
}
