# Volume 17: Production-Grade Authentication & Security Platform

## 1. Executive Summary

Volume 17 establishes the production-grade, hardened **Identity & Access Foundation** and **Security Boundary** for the RegimeX quantitative intelligence platform.

Operating as an authenticated application boundary over the existing RegimeX V16 FastAPI transport and V05–V15 domain capabilities, Volume 17 provides secure user registration, credential authentication, memory-hard Argon2id password protection, signed JWT token issuance, extensible authorization policy checking, and defense-in-depth request security hardening.

```text
                                HTTP Client
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Transport                             │
│                                                                        │
│  • Request ID Sanitization Middleware (X-Request-ID regex & bounds)    │
│  • API Security Headers Middleware (nosniff, DENY, CSP, HSTS)          │
│  • Request Boundary Middleware (Content-Length bounding, HTTP 413)     │
│  • Production-Hardened CORS Middleware (explicit origin allowlist)     │
│  • OpenAPI Security Scheme (HTTPBearer)                                │
│                                                                        │
│  Authentication Endpoints (/api/v1/auth):                              │
│      POST /api/v1/auth/register                                        │
│      POST /api/v1/auth/login                                           │
│      GET  /api/v1/auth/me                                              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
               FastAPI Dependency Injection Boundary
               (CurrentUser, RequireAuthenticatedUser, auth_service_dep)
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Authentication & Authorization Boundary Layer              │
│                                                                        │
│  • Authentication: get_current_user (Bearer extraction & JWT decode)   │
│  • Authorization: require_authenticated_user & AuthorizationChecker    │
│  • Active-User Policy Enforcement (is_active verification)             │
│  • Anti-Enumeration Constant-Time Login Flow                           │
│  • Safe DTO Translation (zero password / credential leakage)           │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│       Password & Token Services       │ │    User Persistence Layer    │
│                                       │ │                              │
│  • Argon2PasswordHasher (Argon2id)   │ │  • SQLAlchemyUserRepository  │
│  • JwtTokenService (PyJWT / HMAC)     │ │  • AsyncSession & Engine     │
│  • Algorithm Allowlist (HS256/384/512)│ │  • PostgreSQL / SQLite       │
│  • Issuer / Audience Verification     │ │  • Unique Normalized Email   │
│  • exp > iat & UUID sub Validation    │ │  • Safe Transaction Rollback │
└───────────────────────────────────────┘ └──────────────────────────────┘
```

> [!IMPORTANT]
> **Explicit Scope Boundary & Deferred Features**:
> **V17 Commit 01 established authentication. V17 Commit 02 hardens the security boundary. Full role/permission authorization remains deferred.**
> 
> Features such as OAuth, Google/Apple/GitHub login, SSO, MFA, WebAuthn/passkeys, password reset email workflows, email verification workflows, session management UI, frontend authentication pages, rate limiting, audit/telemetry platform, and API keys are **not implemented** in this commit and are reserved for future security volumes.

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(auth): implement secure user authentication` | **DONE** |
| **02** | `feat` | `feat(security): harden API authorization and request handling` | **DONE** |

---

## 3. Authentication vs. Authorization Separation

A strict architectural distinction is maintained across the platform:

- **Authentication ("Who is this user?")**:
  Handled by `get_current_user` and `AuthenticationService`. Verifies identity through cryptographic credentials (passwords during login; signed JWT bearer tokens during API calls) and resolves the principal to a durable database record.
- **Authorization ("Is this authenticated identity permitted to perform this operation?")**:
  Handled by `require_authenticated_user` and `AuthorizationChecker`. Evaluates whether the authenticated identity meets required access criteria (e.g. active account status in Commit 02; future roles, permissions, scopes, and resource ownership in subsequent volumes).

### Extensible Authorization Architecture (`app.modules.identity_access.domain.authorization`)
The domain authorization protocol provides a drop-in foundation for future RBAC without rewriting route handlers:
```python
class AuthorizationPolicy(Protocol):
    def check(self, user: UserDTO) -> None: ...

class ActiveUserPolicy:
    def check(self, user: UserDTO) -> None:
        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

class AuthorizationChecker:
    def __init__(self, policies: list[AuthorizationPolicy] | None = None) -> None:
        self._policies = policies or [ActiveUserPolicy()]

    def authorize(self, user: UserDTO) -> None:
        for policy in self._policies:
            policy.check(user)
```

FastAPI routes declare access via:
```python
CurrentUser = Annotated[UserDTO, Depends(require_authenticated_user)]
```
Future volumes can introduce `require_role("analyst")` or `require_permission("market:write")` by extending `AuthorizationPolicy` with zero disruption to existing endpoints.

---

## 4. User Identity Model & Persistence

The user entity is represented at the domain level as an immutable, typed dataclass and persisted via SQLAlchemy 2.0.

### 4.1 Domain Model (`app.modules.identity_access.domain.models.User`)
```python
@dataclass(frozen=True)
class User:
    id: uuid.UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.2 Database Schema (`users` table)
- **`id`**: `UUID` primary key, auto-generated via `uuid.uuid4()`.
- **`email`**: `VARCHAR(320)`, non-nullable, canonical normalized, unique index (`uq_users_email` / `ix_users_email`).
- **`password_hash`**: `VARCHAR(255)`, non-nullable, storing Argon2id hashes. Plaintext passwords are **never persisted**.
- **`is_active`**: `BOOLEAN`, non-nullable, default `TRUE`.
- **`created_at`**: `TIMESTAMP WITH TIME ZONE`, non-nullable, default UTC now.
- **`updated_at`**: `TIMESTAMP WITH TIME ZONE`, non-nullable, default UTC now.

---

## 5. Email Normalization Policy

To prevent account collision, duplication exploits, and casing confusion, a single canonical email normalization policy is applied during **registration**, **login**, and **user lookup**:

1. **Whitespace Trimming**: Strip leading and trailing whitespace characters.
2. **Case Normalization**: Entire email address is lowercased (`email.lower()`).
3. **Format Validation**: Strict regex validation ensuring valid syntax (`<local-part>@<domain>.<tld>`) with length constraints (1–320 chars total, local part ≤ 64 chars).
4. **Provider-Agnostic**: Provider-specific stripping of dots or sub-address aliases (e.g. Gmail `+` tags) is intentionally omitted to maintain compatibility across enterprise email providers.

---

## 6. Password Security & Argon2id Hashing

### 6.1 Cryptographic Algorithm
RegimeX uses **Argon2id** (via `argon2-cffi`), the winner of the Password Hashing Competition (PHC) and a memory-hard password hashing algorithm:
- Cryptographically secure, unique salt per password hash generated automatically.
- Resists GPU/ASIC brute-force attacks via tuned time and memory cost parameters.
- Constant-time verification behavior supplied by the underlying CFFI implementation (`verify`).
- Legacy or insecure algorithms (MD5, SHA-1, SHA-256, plain SHA-512, reversible encryption) are strictly prohibited.

### 6.2 Password Policy
- **Minimum Length**: 12 characters (`len(password) >= 12`).
- **Rejection of Empty Passwords**: Passwords consisting of only whitespace or empty strings are rejected.
- **Composition**: Arbitrary composition rules that degrade entropy without improving security are omitted, following NIST SP 800-63B guidelines.
- **Sanitization**: Plaintext passwords are never logged, never included in exception messages, and never returned in API responses.

---

## 7. JWT Security Hardening & Token Design

### 7.1 JWT Specifications & Claim Validation
Signed JSON Web Tokens (JWT) adhering to RFC 7519 are strictly hardened:
- **Mandatory Claims**: `sub`, `email`, `jti`, `iat`, `exp`.
- **Subject Validation**: The `sub` claim is strictly validated as a valid UUID string. Non-UUID or malformed subjects are rejected.
- **Timestamp Integrity**: `iat` and `exp` must be numeric integers, timezone-aware UTC. `exp` must be strictly greater than `iat` (`exp > iat`).
- **Algorithm Allowlist**: Restricted to HMAC SHA-2 (`HS256`, `HS384`, `HS512`). The unverified `alg` header from incoming tokens is never trusted; decoding explicitly enforces `algorithms=[self._algorithm]`. The insecure `none` algorithm is rejected at initialization and token evaluation.
- **Issuer (`iss`) & Audience (`aud`) Verification**:
  - Configurable via `AUTH_JWT_ISSUER` and `AUTH_JWT_AUDIENCE`.
  - When configured, tokens include `iss` and `aud` on issuance, and incoming tokens are strictly validated against them. Mismatches or omitted claims raise `InvalidTokenError`.
  - When unconfigured, claims remain optional for backward compatibility.
- **Clock Skew Leeway**: Configurable via `leeway_seconds` (default: `0`). Negative values are rejected.

---

## 8. HTTP Security & Boundary Hardening

### 8.1 API Security Headers (`app.core.middleware.security_headers_middleware`)
Every HTTP response carries protective headers:
- **`X-Content-Type-Options: nosniff`**: Prevents browser MIME-type sniffing.
- **`X-Frame-Options: DENY`**: Protects against clickjacking by prohibiting iframe embedding.
- **`Referrer-Policy: strict-origin-when-cross-origin`**: Protects sensitive path information from leaking in external referrers.
- **`Permissions-Policy`**: Disables unused browser device features (`camera=(), microphone=(), geolocation=(), ...`).
- **`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`**: Strict API CSP for all endpoints (exempting `/docs` and `/redoc` in development to preserve Swagger UI).
- **`Strict-Transport-Security` (HSTS)**:
  - Attached **only** when requests are served over HTTPS (`X-Forwarded-Proto: https` or `https://`) or in production environments.
  - **Never** attached during plain local HTTP development, preventing local environment breakage.

### 8.2 Request-ID Sanitization & Protection (`app.core.middleware.request_id_middleware`)
- Incoming `X-Request-ID` headers are validated against a strict regex: `^[A-Za-z0-9_\-]{1,64}$`.
- Oversized IDs (>64 chars) or IDs containing CRLF characters (`\r`, `\n`) or special symbols are discarded to prevent HTTP response splitting and log injection.
- Discarded or omitted IDs are replaced with fresh cryptographically random UUID4 strings.

### 8.3 Request Boundary Protection (`app.core.middleware.request_boundary_middleware`)
- Bounded payload sizes via `Content-Length` inspection.
- Rejects requests exceeding `MAX_REQUEST_BODY_BYTES` (default: 10 MB) with `413 Payload Too Large` (`PAYLOAD_TOO_LARGE`).
- Malformed or negative `Content-Length` headers return `400 Bad Request`.

### 8.4 Production-Hardened CORS
- Configuration via `CORS_ALLOWED_ORIGINS` / `REGIMEX_CORS_ALLOWED_ORIGINS`.
- Accepts list of strings or comma-separated environment strings.
- **Production Guard**: Wildcard origin `*` is strictly forbidden in production mode (`Environment.PRODUCTION`).
- Credentials are only enabled when origins do not contain `*`.

---

## 9. Logging & Secrets Safety

- **Zero Credential Logging**: Authorization headers, Bearer tokens, passwords, password hashes, and database connection secrets are never logged.
- **Sanitized Diagnostics**: Log messages capture only safe request metadata (`request_id`, status, endpoint path).
- **Response Isolation**: Secrets and database credentials are verified absent from:
  - Root metadata (`/`)
  - Operational probes (`/health`, `/ready`)
  - Dynamic OpenAPI specification (`/openapi.json`)
  - Exception envelopes (`ApiError`)

---

## 10. Error Contract & Mapping

All authentication and authorization errors map directly into the standard RegimeX `ApiError` envelope:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required.",
    "request_id": "951244c9-84a3-43e2-aba8-c2d038a0c51e",
    "details": null
  }
}
```

| Domain Error | HTTP Status | Error Code | Description |
| :--- | :---: | :--- | :--- |
| `AuthenticationRequiredError` | `401` | `AUTHENTICATION_REQUIRED` | Missing or invalid Authorization header scheme. |
| `InvalidTokenError` | `401` | `AUTHENTICATION_REQUIRED` | Malformed token, bad signature, or invalid claims. |
| `ExpiredTokenError` | `401` | `AUTHENTICATION_REQUIRED` | Expired access token. |
| `InvalidCredentialsError` | `401` | `INVALID_CREDENTIALS` | Invalid email or incorrect password (anti-enumeration). |
| `InactiveUserError` | `401` | `AUTHENTICATION_REQUIRED` | Account deactivated by administrative action. |
| `AuthorizationError` | `403` | `FORBIDDEN` | Caller lacks permissions for the requested resource. |
| `DuplicateEmailError` | `409` | `DUPLICATE_EMAIL` | Account with normalized email already exists. |
| `InvalidPasswordError` | `422` | `INVALID_PASSWORD` | Password does not meet 12-character minimum policy. |
| `InvalidEmailError` | `422` | `INVALID_EMAIL` | Email format is invalid or exceeds length bounds. |

---

## 11. Verification & Quality Gates

The authentication and security platform has passed all quality gates:

| Gate | Command | Result |
| :--- | :--- | :---: |
| **Pytest Full Suite** | `python -m pytest -q` | **PASS (1,281 passed, 1 skipped)** |
| **API & Security Tests** | `python -m pytest -v tests/api/` | **PASS (112 passed)** |
| **Unit Identity & Security Tests** | `python -m pytest -v tests/unit/identity_access/` | **PASS (52 passed)** |
| **Ruff Linter** | `python -m ruff check app tests` | **PASS (0 warnings, 0 errors)** |
| **Ruff Formatter** | `python -m ruff format --check app tests` | **PASS (354 files clean)** |
| **Mypy Static Typing** | `python -m mypy app tests` | **PASS (354 source files)** |
| **Frontend Lint** | `npm run lint` (apps/web) | **PASS (0 warnings, 0 errors)** |
| **Frontend Type-Check** | `npm run type-check` (apps/web) | **PASS (clean)** |
| **Alembic Migration** | `alembic upgrade head && alembic downgrade -1` | **PASS (clean)** |
