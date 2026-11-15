import { getMockResponse } from "./mock-data";
import { ApiError, apiErrorFromResponse, jsonFromResponse } from "./api-error";

export { ApiError } from "./api-error";

const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

/**
 * Browser requests use the same-origin Next.js proxy so backend credentials
 * and the Clerk session token stay server-side.
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${normalizedPath}`, {
      ...init,
      headers,
    });
  } catch {
    if (method === "GET" && USE_MOCK_API) {
      const mock = getMockResponse<T>(normalizedPath);
      if (mock !== null) return mock;
    }

    throw new ApiError(
      0,
      "NETWORK_ERROR",
      `Could not connect to the backend for ${normalizedPath}`
    );
  }

  if (!response.ok) {
    throw await apiErrorFromResponse(response);
  }
  return jsonFromResponse<T>(response);
}
