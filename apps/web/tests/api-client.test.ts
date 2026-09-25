import test from "node:test";
import assert from "node:assert";
import { apiFetch, buildApiUrl } from "../lib/api/client";
import { RegimeXApiError } from "../lib/api/errors";
import { listMarkets, getMarketData, getMarketRegime, getRegimeTransitions } from "../lib/api/markets";

test("API Client — buildApiUrl respects prefixes and normalization", () => {
  assert.strictEqual(
    buildApiUrl("/markets", "http://localhost:8000"),
    "http://localhost:8000/api/v1/markets"
  );
  assert.strictEqual(
    buildApiUrl("/api/v1/markets", "http://localhost:8000/"),
    "http://localhost:8000/api/v1/markets"
  );
  assert.strictEqual(
    buildApiUrl("/health", "http://localhost:8000"),
    "http://localhost:8000/health"
  );
});

test("API Client — successful response parsing", async () => {
  const mockPayload = {
    items: [
      { symbol: "SPY", asset_class: "equity_us", exchange: "ARCA", currency: "USD", description: "S&P 500 ETF" }
    ],
    total: 1,
    limit: 100,
    offset: 0,
  };

  const customFetch = (async () => {
    return new Response(JSON.stringify(mockPayload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;

  const result = await listMarkets({}, { fetchFn: customFetch });
  assert.strictEqual(result.total, 1);
  assert.strictEqual(result.items[0].symbol, "SPY");
});

test("API Client — API error envelope and request ID extraction", async () => {
  const errorEnvelope = {
    error: {
      code: "VALIDATION_ERROR",
      message: "Query end must be strictly after start.",
      request_id: "req_test_12345",
      details: { start: "2024-01-02", end: "2024-01-01" },
    },
  };

  const customFetch = (async () => {
    return new Response(JSON.stringify(errorEnvelope), {
      status: 422,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": "req_test_12345",
      },
    });
  }) as unknown as typeof fetch;

  await assert.rejects(
    async () => {
      await getMarketData(
        "SPY",
        { start: "2024-01-02T00:00:00Z", end: "2024-01-01T00:00:00Z" },
        { fetchFn: customFetch }
      );
    },
    (err: unknown) => {
      assert.ok(err instanceof RegimeXApiError, "Error must be instance of RegimeXApiError");
      assert.strictEqual(err.code, "VALIDATION_ERROR");
      assert.strictEqual(err.status, 422);
      assert.strictEqual(err.requestId, "req_test_12345");
      assert.strictEqual(err.kind, "validation_failure");
      assert.strictEqual(err.message, "Query end must be strictly after start.");
      return true;
    }
  );
});

test("API Client — network failure translation", async () => {
  const customFetch = (async () => {
    throw new TypeError("fetch failed: connection refused");
  }) as unknown as typeof fetch;

  await assert.rejects(
    async () => {
      await apiFetch("/markets", { fetchFn: customFetch });
    },
    (err: unknown) => {
      assert.ok(err instanceof RegimeXApiError);
      assert.strictEqual(err.kind, "network_failure");
      assert.strictEqual(err.status, 0);
      assert.ok(err.message.includes("Unable to connect to the RegimeX server"));
      return true;
    }
  );
});

test("API Client — authentication failure (HTTP 401)", async () => {
  const errorEnvelope = {
    error: {
      code: "AUTHENTICATION_REQUIRED",
      message: "Valid Bearer token required.",
      request_id: "req_auth_999",
    },
  };

  const customFetch = (async () => {
    return new Response(JSON.stringify(errorEnvelope), {
      status: 401,
      headers: { "Content-Type": "application/json", "X-Request-ID": "req_auth_999" },
    });
  }) as unknown as typeof fetch;

  await assert.rejects(
    async () => {
      await apiFetch("/auth/me", { fetchFn: customFetch });
    },
    (err: unknown) => {
      assert.ok(err instanceof RegimeXApiError);
      assert.strictEqual(err.kind, "authentication_failure");
      assert.strictEqual(err.status, 401);
      assert.strictEqual(err.isAuthError, true);
      assert.strictEqual(err.requestId, "req_auth_999");
      return true;
    }
  );
});

test("API Client — market regime and transition endpoints query formatting", async () => {
  let capturedUrl = "";

  const customFetch = (async (url: string) => {
    capturedUrl = url;
    return new Response(JSON.stringify({ symbol: "BTC-USD" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;

  await getMarketRegime("btc-usd", { limit: 50 }, { fetchFn: customFetch });
  assert.ok(capturedUrl.includes("/markets/BTC-USD/regime?limit=50"));

  await getRegimeTransitions("btc-usd", {}, { fetchFn: customFetch });
  assert.ok(capturedUrl.includes("/markets/BTC-USD/regime/transitions"));
});
