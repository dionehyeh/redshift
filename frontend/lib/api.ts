// Client-side API helper — routes all calls through Next.js /api/* proxy
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `/api${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    },
  });

  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = data as {
      error?: { code?: string; message?: string };
      detail?: string;
    };
    throw new ApiError(
      error.error?.message || error.detail || `Request failed with status ${res.status}`,
      res.status,
      error.error?.code || "REQUEST_FAILED",
    );
  }
  return data as T;
}
