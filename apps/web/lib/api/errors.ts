/**
 * RegimeX Web — API Error Handling Foundation
 * ============================================
 * Provides typed, classified, user-safe error representations for all
 * network and API communication failures.
 *
 * Architecture rules:
 *   - Parses standard RegimeX backend error envelope: { error: { code, message, request_id, details } }
 *   - Preserves request_id correlation tokens for telemetry and user support.
 *   - Converts raw fetch and HTTP failures into classified, safe UI messages.
 *   - Never leaks sensitive internal details, database queries, or server stack traces.
 */

import type { ApiErrorDetail } from "./types";

export type ApiErrorKind =
  | "network_failure"
  | "validation_failure"
  | "authentication_failure"
  | "authorization_failure"
  | "not_found"
  | "conflict"
  | "rate_limit"
  | "server_error"
  | "unknown_failure";

export class RegimeXApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly kind: ApiErrorKind;
  public readonly requestId?: string;
  public readonly details?: unknown;

  constructor(params: {
    message: string;
    code?: string;
    status?: number;
    kind?: ApiErrorKind;
    requestId?: string;
    details?: unknown;
  }) {
    super(params.message);
    this.name = "RegimeXApiError";
    this.status = params.status ?? 0;
    this.code = params.code ?? "UNKNOWN_ERROR";
    this.requestId = params.requestId;
    this.details = params.details;

    if (params.kind) {
      this.kind = params.kind;
    } else {
      this.kind = RegimeXApiError.classifyKind(this.status, this.code);
    }
  }

  /**
   * Classify error into a high-level architectural category.
   */
  public static classifyKind(status: number, code: string): ApiErrorKind {
    if (status === 0 || code === "NETWORK_ERROR") {
      return "network_failure";
    }
    if (status === 401 || code === "AUTHENTICATION_REQUIRED") {
      return "authentication_failure";
    }
    if (status === 403 || code === "PERMISSION_DENIED") {
      return "authorization_failure";
    }
    if (status === 404 || code === "NOT_FOUND") {
      return "not_found";
    }
    if (status === 409 || code === "CONFLICT") {
      return "conflict";
    }
    if (status === 422 || code === "VALIDATION_ERROR") {
      return "validation_failure";
    }
    if (status === 429 || code === "RATE_LIMIT_EXCEEDED") {
      return "rate_limit";
    }
    if (status >= 500) {
      return "server_error";
    }
    return "unknown_failure";
  }

  /**
   * Create an error instance from an HTTP response and parsed error envelope.
   */
  public static fromBackend(
    status: number,
    payload: unknown,
    headerRequestId?: string | null
  ): RegimeXApiError {
    let code = "UNKNOWN_ERROR";
    let message = "An unexpected server error occurred.";
    let requestId = headerRequestId ?? undefined;
    let details: unknown = undefined;

    if (payload && typeof payload === "object" && "error" in payload) {
      const errObj = (payload as { error: Partial<ApiErrorDetail> }).error;
      if (errObj.code) code = String(errObj.code);
      if (errObj.message) message = String(errObj.message);
      if (errObj.request_id) requestId = String(errObj.request_id);
      if (errObj.details !== undefined) details = errObj.details;
    }

    return new RegimeXApiError({
      message,
      code,
      status,
      requestId,
      details,
    });
  }

  /**
   * Create a network failure error instance (fetch rejected or offline).
   */
  public static networkFailure(error?: unknown): RegimeXApiError {
    return new RegimeXApiError({
      message: "Unable to connect to the RegimeX server. Please verify your network connection.",
      code: "NETWORK_ERROR",
      status: 0,
      kind: "network_failure",
      details: error instanceof Error ? error.message : undefined,
    });
  }

  /**
   * Helper properties for convenient checking.
   */
  public get isNetworkError(): boolean {
    return this.kind === "network_failure";
  }

  public get isAuthError(): boolean {
    return this.kind === "authentication_failure" || this.kind === "authorization_failure";
  }

  public get isValidationError(): boolean {
    return this.kind === "validation_failure";
  }
}

/**
 * Returns a user-safe title and description for display in UI error boundaries and states.
 */
export function toUserFacingMessage(error: unknown): {
  title: string;
  message: string;
  requestId?: string;
} {
  if (error instanceof RegimeXApiError) {
    let title = "Request Failed";
    switch (error.kind) {
      case "network_failure":
        title = "Connection Error";
        break;
      case "authentication_failure":
        title = "Authentication Required";
        break;
      case "authorization_failure":
        title = "Access Denied";
        break;
      case "not_found":
        title = "Resource Not Found";
        break;
      case "validation_failure":
        title = "Invalid Request Parameters";
        break;
      case "rate_limit":
        title = "Rate Limit Exceeded";
        break;
      case "server_error":
        title = "Server Error";
        break;
      default:
        title = "Application Error";
    }

    return {
      title,
      message: error.message,
      requestId: error.requestId,
    };
  }

  return {
    title: "Application Error",
    message: "An unexpected error occurred while processing your request. Please try again.",
  };
}
