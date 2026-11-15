import { auth } from "@clerk/nextjs/server";
import { getMockResponse } from "./mock-data";
import { ApiError, apiErrorFromResponse, jsonFromResponse } from "./api-error";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

export async function serverApi<T>(path: string): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const authSession = await auth();
  const token = await authSession.getToken();

  let response: Response;
  try {
    response = await fetch(
      `${API_BASE.replace(/\/+$/, "")}/api/v1${normalizedPath}`,
      {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        cache: "no-store",
      }
    );
  } catch {
    if (USE_MOCK_API) {
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
