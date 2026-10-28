import test from "node:test";
import assert from "node:assert";
import {
  normalizeApiBaseUrl,
  getApiBaseUrl,
  getAppName,
  getAppVersion,
  isInternalContainerUrl,
} from "../lib/config/env";

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

  // Internal Docker hostnames must not be shipped as client URLs
  assert.strictEqual(isInternalContainerUrl("http://api:8000"), true);
  assert.strictEqual(isInternalContainerUrl("http://regimex-api:8000"), true);
  assert.strictEqual(isInternalContainerUrl("http://redis:6379"), true);
  assert.strictEqual(isInternalContainerUrl("http://localhost:8000"), false);
  assert.strictEqual(isInternalContainerUrl("https://api.regimex.io"), false);

  assert.strictEqual(normalizeApiBaseUrl("http://api:8000"), "http://localhost:8000");
  assert.strictEqual(normalizeApiBaseUrl("http://regimex-api:8000"), "http://localhost:8000");
});

test("Environment Configuration — fallback getters", () => {
  const url = getApiBaseUrl();
  assert.ok(url.startsWith("http://") || url.startsWith("https://"));

  const appName = getAppName();
  assert.ok(appName.length > 0);

  const version = getAppVersion();
  assert.ok(version.length > 0);
});
