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

const INTERNAL_CONTAINER_HOSTNAMES = new Set([
  "api",
  "regimex-api",
  "web",
  "regimex-web",
  "db",
  "regimex-db",
  "redis",
  "regimex-redis",
]);

/**
 * Checks whether a given URL points to an internal Docker container hostname
 * that cannot be resolved by external client browsers.
 */
export function isInternalContainerUrl(rawUrl: string): boolean {
  try {
    const parsed = new URL(rawUrl);
    return INTERNAL_CONTAINER_HOSTNAMES.has(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

/**
 * Normalizes an API base URL by trimming whitespace, removing trailing slashes,
 * verifying protocol safety, and preventing internal Docker hostnames from
 * being shipped as browser-facing client URLs.
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

  // Prevent internal Docker container hostnames from being used as client URLs
  if (isInternalContainerUrl(stripped)) {
    if (typeof console !== "undefined" && typeof console.warn === "function") {
      console.warn(
        `[RegimeX Web] Warning: NEXT_PUBLIC_API_URL points to internal container hostname "${stripped}". Browser clients cannot resolve Docker internal hostnames. Falling back to "${DEFAULT_API_BASE_URL}".`
      );
    }
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
