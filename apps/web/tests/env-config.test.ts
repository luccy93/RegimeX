import test from "node:test";
import assert from "node:assert";
import { normalizeApiBaseUrl, getApiBaseUrl, getAppName, getAppVersion } from "../lib/config/env";

test("Environment Configuration — normalizeApiBaseUrl sanitization", () => {
  // Valid http URL with trailing slashes
  assert.strictEqual(
    normalizeApiBaseUrl("http://localhost:8000///"),
    "http://localhost:8000"
  );

  // Valid https URL
  assert.strictEqual(
    normalizeApiBaseUrl("https://api.regimex.io"),
    "https://api.regimex.io"
  );

  // Whitespace trimming
  assert.strictEqual(
    normalizeApiBaseUrl("  https://api.regimex.io/  "),
    "https://api.regimex.io"
  );

  // Null / undefined / empty string fallback to default
  assert.strictEqual(normalizeApiBaseUrl(null), "http://localhost:8000");
  assert.strictEqual(normalizeApiBaseUrl(undefined), "http://localhost:8000");
  assert.strictEqual(normalizeApiBaseUrl("   "), "http://localhost:8000");

  // Invalid protocol fallback to default for safety
  assert.strictEqual(normalizeApiBaseUrl("javascript:alert(1)"), "http://localhost:8000");
  assert.strictEqual(normalizeApiBaseUrl("file:///etc/passwd"), "http://localhost:8000");
});

test("Environment Configuration — fallback getters", () => {
  const url = getApiBaseUrl();
  assert.ok(url.startsWith("http://") || url.startsWith("https://"));

  const appName = getAppName();
  assert.ok(appName.length > 0);

  const version = getAppVersion();
  assert.ok(version.length > 0);
});
