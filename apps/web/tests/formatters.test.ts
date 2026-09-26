import test from "node:test";
import assert from "node:assert";
import {
  formatPrice,
  formatPercent,
  formatDate,
  formatDuration,
  formatNumber,
} from "../lib/utils/formatters";

test("Formatters — formatPrice", () => {
  assert.strictEqual(formatPrice(512.45), "$512.45");
  assert.strictEqual(formatPrice(0), "$0.00");
  assert.strictEqual(formatPrice(-15.2), "-$15.20");
  assert.strictEqual(formatPrice(null), "—");
  assert.strictEqual(formatPrice(undefined), "—");
  assert.strictEqual(formatPrice(Number.NaN), "—");
  assert.strictEqual(formatPrice(Infinity), "—");
});

test("Formatters — formatPercent", () => {
  // Ratio mode (default)
  assert.strictEqual(formatPercent(0.0425), "4.25%");
  assert.strictEqual(formatPercent(0.0425, { includeSign: true }), "+4.25%");
  assert.strictEqual(formatPercent(-0.021, { includeSign: true }), "−2.10%");
  assert.strictEqual(formatPercent(0, { includeSign: true }), "0.00%");

  // Raw percent mode
  assert.strictEqual(formatPercent(88.4, { isRatio: false, decimals: 1 }), "88.4%");

  // Edge cases
  assert.strictEqual(formatPercent(null), "—");
  assert.strictEqual(formatPercent(undefined), "—");
  assert.strictEqual(formatPercent(Number.NaN), "—");
});

test("Formatters — formatDate", () => {
  const iso = "2026-09-24T14:30:00Z";
  assert.ok(formatDate(iso, "short").includes("2026"));
  assert.ok(formatDate(iso, "short").includes("Sep"));
  assert.strictEqual(formatDate(iso, "date-only"), "2026-09-24");
  assert.ok(formatDate(iso, "time-only").includes("14:30"));
  assert.strictEqual(formatDate(null), "—");
  assert.strictEqual(formatDate("invalid-date"), "—");
});

test("Formatters — formatDuration", () => {
  assert.strictEqual(formatDuration(1), "1 bar");
  assert.strictEqual(formatDuration(8), "8 bars");
  assert.strictEqual(formatDuration(12.4), "12.4 bars");
  assert.strictEqual(formatDuration(5, "day"), "5 days");
  assert.strictEqual(formatDuration(null), "—");
  assert.strictEqual(formatDuration(undefined), "—");
});

test("Formatters — formatNumber", () => {
  assert.strictEqual(formatNumber(1234.56), "1,234.56");
  assert.ok(formatNumber(45000000, { compact: true }).includes("45"));
  assert.strictEqual(formatNumber(null), "—");
  assert.strictEqual(formatNumber(undefined), "—");
});
