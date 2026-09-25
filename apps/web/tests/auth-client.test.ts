import test from "node:test";
import assert from "node:assert";
import {
  login,
  register,
  getCurrentUser,
  logout,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
} from "../lib/api/auth";

test("Auth Client — in-memory token lifecycle", () => {
  clearAuthToken();
  assert.strictEqual(getAuthToken(), null);

  setAuthToken("jwt_sample_token_xyz");
  assert.strictEqual(getAuthToken(), "jwt_sample_token_xyz");

  logout();
  assert.strictEqual(getAuthToken(), null);
});

test("Auth Client — login records token and returns payload", async () => {
  clearAuthToken();

  const mockResponse = {
    access_token: "signed_jwt_token_123",
    token_type: "bearer",
    expires_in: 3600,
    user: {
      id: "11111111-1111-1111-1111-111111111111",
      email: "trader@regimex.io",
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
    },
  };

  const customFetch = (async () => {
    return new Response(JSON.stringify(mockResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;

  const result = await login(
    { email: "trader@regimex.io", password: "Password12345!" },
    { fetchFn: customFetch }
  );

  assert.strictEqual(result.access_token, "signed_jwt_token_123");
  assert.strictEqual(result.user.email, "trader@regimex.io");
  assert.strictEqual(getAuthToken(), "signed_jwt_token_123");
});

test("Auth Client — getCurrentUser sends Bearer authorization header", async () => {
  setAuthToken("valid_user_jwt");

  let receivedAuthHeader: string | null = null;
  const customFetch = (async (_url: string, init?: RequestInit) => {
    receivedAuthHeader = (init?.headers as Record<string, string>)["Authorization"] ?? null;
    return new Response(
      JSON.stringify({
        id: "11111111-1111-1111-1111-111111111111",
        email: "trader@regimex.io",
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }) as unknown as typeof fetch;

  await getCurrentUser(null, { fetchFn: customFetch });
  assert.strictEqual(receivedAuthHeader, "Bearer valid_user_jwt");

  clearAuthToken();
});

test("Auth Client — register submits credentials to /auth/register", async () => {
  let requestPath = "";
  const customFetch = (async (url: string) => {
    requestPath = url;
    return new Response(
      JSON.stringify({
        user: {
          id: "22222222-2222-2222-2222-222222222222",
          email: "newuser@regimex.io",
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
        },
      }),
      { status: 201, headers: { "Content-Type": "application/json" } }
    );
  }) as unknown as typeof fetch;

  const response = await register(
    { email: "newuser@regimex.io", password: "SecurePassword123!" },
    { fetchFn: customFetch }
  );

  assert.ok(requestPath.includes("/auth/register"));
  assert.strictEqual(response.user.email, "newuser@regimex.io");
});
