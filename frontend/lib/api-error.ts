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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function apiErrorFromResponse(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const error = isRecord(payload) && isRecord(payload.error) ? payload.error : {};
  const code = typeof error.code === "string" ? error.code : "HTTP_ERROR";
  const message =
    typeof error.message === "string"
      ? error.message
      : response.statusText || "The API request failed";
  const details = isRecord(error.details) ? error.details : undefined;

  return new ApiError(response.status, code, message, details);
}

export async function jsonFromResponse<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      response.status,
      "INVALID_RESPONSE",
      "The API returned an invalid JSON response"
    );
  }
}
