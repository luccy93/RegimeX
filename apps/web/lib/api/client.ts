/**
 * RegimeX Web — Typed API Client Foundation
 * ==========================================
 * Typed HTTP transport client communicating with the RegimeX FastAPI backend.
 *
 * Enforces:
 *   - Environment-driven base URL configuration via getApiBaseUrl().
 *   - Standard content-type and accept headers.
 *   - Bearer token authorization header injection when authenticated.
 *   - Error boundary translation via RegimeXApiError.
 *   - Request correlation via X-Request-ID preservation.
 */

import { getApiBaseUrl } from "../config/env";
import { RegimeXApiError } from "./errors";

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  token?: string | null;
  /** Custom fetch implementation (useful for unit testing). */
  fetchFn?: typeof fetch;
}

/**
 * Builds the canonical request URL.
 */
export function buildApiUrl(path: string, baseUrl: string = getApiBaseUrl()): string {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // If path already starts with /api or /health or /ready, use directly
  if (
    normalizedPath.startsWith("/api/") ||
    normalizedPath.startsWith("/health") ||
    normalizedPath.startsWith("/ready") ||
    normalizedPath === "/"
  ) {
    return `${normalizedBase}${normalizedPath}`;
  }

  // Otherwise, default to /api/v1 prefix
  return `${normalizedBase}/api/v1${normalizedPath}`;
}

/**
 * Core typed fetch wrapper.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, token, fetchFn, ...fetchOptions } = options;
  const activeFetch = fetchFn ?? fetch;
  const url = buildApiUrl(path);

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await activeFetch(url, {
      ...fetchOptions,
      headers: {
        ...headers,
        ...(fetchOptions.headers as Record<string, string>),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw RegimeXApiError.networkFailure(error);
  }

  const requestId = response.headers.get("x-request-id") || response.headers.get("X-Request-ID");

  if (!response.ok) {
    let errorPayload: unknown;
    try {
      errorPayload = await response.json();
    } catch {
      errorPayload = null;
    }

    throw RegimeXApiError.fromBackend(response.status, errorPayload, requestId);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  try {
    const data = (await response.json()) as T;
    return data;
  } catch (parseError) {
    throw new RegimeXApiError({
      message: "Received invalid JSON response from the server.",
      code: "INVALID_JSON_RESPONSE",
      status: response.status,
      kind: "server_error",
      requestId: requestId ?? undefined,
      details: parseError instanceof Error ? parseError.message : undefined,
    });
  }
}
