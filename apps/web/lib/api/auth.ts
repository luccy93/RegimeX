/**
 * RegimeX Web — Authentication Client Foundation
 * ===============================================
 * Client-side boundary for user authentication corresponding to
 * backend /api/v1/auth endpoints (Volume 17 Commit 01).
 *
 * Security Principles:
 *   - NEVER persist passwords.
 *   - NEVER log passwords, access tokens, or Authorization headers.
 *   - NEVER put tokens in URLs or query strings.
 *   - Access tokens are held in-memory by default.
 *   - Clean logout semantics invalidate the in-memory state.
 *   - No refresh-token mechanism is invented; adheres to backend contracts.
 */

import { apiFetch, type RequestOptions } from "./client";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserResponse,
} from "./types";

/**
 * Pluggable token storage contract for the authentication client.
 * In-memory by default to prevent unauthorized persistent disk/local storage access.
 */
export interface AuthTokenStorage {
  getToken(): string | null;
  setToken(token: string): void;
  clearToken(): void;
}

class MemoryTokenStorage implements AuthTokenStorage {
  private token: string | null = null;

  public getToken(): string | null {
    return this.token;
  }

  public setToken(token: string): void {
    this.token = token;
  }

  public clearToken(): void {
    this.token = null;
  }
}

// Global active token storage instance (in-memory)
let defaultStorage: AuthTokenStorage = new MemoryTokenStorage();

/**
 * Configure a custom token storage adapter if required.
 */
export function setAuthTokenStorage(storage: AuthTokenStorage): void {
  defaultStorage = storage;
}

/**
 * Get the current active authentication token.
 */
export function getAuthToken(): string | null {
  return defaultStorage.getToken();
}

/**
 * Set the current active authentication token.
 */
export function setAuthToken(token: string): void {
  defaultStorage.setToken(token);
}

/**
 * Clear the current authentication token.
 */
export function clearAuthToken(): void {
  defaultStorage.clearToken();
}

/**
 * Register a new user account.
 */
export async function register(
  payload: RegisterRequest,
  options?: RequestOptions
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/auth/register", {
    ...options,
    method: "POST",
    body: payload,
  });
}

/**
 * Authenticate credentials and receive a signed JWT access token.
 * Automatically records the token in memory upon success.
 */
export async function login(
  payload: LoginRequest,
  options?: RequestOptions
): Promise<LoginResponse> {
  const result = await apiFetch<LoginResponse>("/auth/login", {
    ...options,
    method: "POST",
    body: payload,
  });

  if (result?.access_token) {
    setAuthToken(result.access_token);
  }

  return result;
}

/**
 * Fetch the current authenticated user's profile identity.
 */
export async function getCurrentUser(
  tokenOverride?: string | null,
  options?: RequestOptions
): Promise<UserResponse> {
  const activeToken = tokenOverride ?? getAuthToken();

  return apiFetch<UserResponse>("/auth/me", {
    ...options,
    method: "GET",
    token: activeToken,
  });
}

/**
 * Logout clears the active authentication session.
 */
export function logout(): void {
  clearAuthToken();
}
