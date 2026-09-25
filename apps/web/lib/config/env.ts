/**
 * RegimeX Web — Environment Configuration
 *
 * Strict, typed boundary for accessing browser-safe environment variables.
 * Enforces security boundaries:
 *   - Only NEXT_PUBLIC_* variables are permitted in browser bundles.
 *   - Normalizes URLs (strips trailing slashes).
 *   - Validates that URLs use safe protocols (http/https).
 *   - Never stores or reads backend secrets.
 */

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_APP_NAME = "RegimeX";
const DEFAULT_APP_VERSION = "0.1.0";

/**
 * Normalizes an API base URL by trimming whitespace, removing trailing slashes,
 * and ensuring an allowed HTTP/HTTPS scheme.
 */
export function normalizeApiBaseUrl(rawUrl?: string | null): string {
  if (!rawUrl || typeof rawUrl !== "string") {
    return DEFAULT_API_BASE_URL;
  }

  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }

  // Remove trailing slashes
  const stripped = trimmed.replace(/\/+$/, "");

  // Basic security check: ensure valid protocol
  if (!stripped.startsWith("http://") && !stripped.startsWith("https://")) {
    // If invalid format or protocol, fall back to safe default
    return DEFAULT_API_BASE_URL;
  }

  return stripped;
}

/**
 * Returns the resolved RegimeX FastAPI base URL.
 * Checks NEXT_PUBLIC_API_URL, then NEXT_PUBLIC_API_BASE_URL, with localhost fallback.
 */
export function getApiBaseUrl(): string {
  const envUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL;

  return normalizeApiBaseUrl(envUrl);
}

/**
 * Returns the public application name.
 */
export function getAppName(): string {
  return process.env.NEXT_PUBLIC_APP_NAME || DEFAULT_APP_NAME;
}

/**
 * Returns the public application release version.
 */
export function getAppVersion(): string {
  return process.env.NEXT_PUBLIC_APP_VERSION || DEFAULT_APP_VERSION;
}

/**
 * Returns true if the application is running in production mode.
 */
export function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}
