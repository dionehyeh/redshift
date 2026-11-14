export const ERROR_MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: "Please sign in to access your farm records.",
  FORBIDDEN: "You do not have permission to view this resource.",
  NOT_FOUND: "The requested resource was not found.",
  FIELD_NOT_READY: "Field soil and climate profile is still building. Please wait a moment.",
  CROP_REQUIRED: "Please specify a target crop for farmer-led evaluation.",
  VALIDATION: "Invalid inputs provided. Please check the highlighted fields.",
  CONSENT_REQUIRED: "Please select at least one data category to share with your advisor.",
  REPORT_UNAVAILABLE: "This consultation report has expired or was revoked.",
  DATA_UNAVAILABLE: "External satellite source temporarily unavailable. Showing cached data.",
  INTERNAL: "An unexpected server error occurred. Please try again.",
};

export function getErrorMessage(code: string): string {
  return ERROR_MESSAGES[code] || "An unexpected error occurred. Please try again.";
}
