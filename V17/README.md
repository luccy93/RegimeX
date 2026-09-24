# Volume 17: Production-Grade Authentication & Security Platform

## 1. Executive Summary

Volume 17 establishes the production-grade, hardened **Identity & Access Foundation** for the RegimeX quantitative intelligence platform.

Operating as an authenticated application boundary over the existing RegimeX V16 FastAPI transport and V05–V15 domain capabilities, Volume 17 Commit 01 provides secure user registration, credential authentication, memory-hard password protection, and signed JWT token issuance and validation.

```text
                                HTTP Client
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Transport                             │
│                                                                        │
│  • Request Correlation ID Middleware (X-Request-ID)                     │
│  • OpenAPI Security Scheme (HTTPBearer)                                │
│  • Authentication Endpoints (/api/v1/auth):                            │
│      POST /api/v1/auth/register                                        │
│      POST /api/v1/auth/login                                           │
│      GET  /api/v1/auth/me                                              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
               FastAPI Dependency Injection Boundary
               (CurrentUser, auth_service_dep, etc.)
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  Authentication Application Service                    │
│                                                                        │
│  • Canonical Email Normalization & Password Policy Enforcement         │
│  • Anti-Enumeration Constant-Time Login Flow                           │
│  • Subject Identity Resolution & Safe DTO Translation                  │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│       Password & Token Services       │ │    User Persistence Layer    │
│                                       │ │                              │
│  • Argon2PasswordHasher (Argon2id)   │ │  • SQLAlchemyUserRepository  │
│  • JwtTokenService (PyJWT / HMAC)     │ │  • AsyncSession & Engine     │
│  • Typed TokenClaims Verification     │ │  • PostgreSQL / SQLite       │
└───────────────────────────────────────┘ └──────────────────────────────┘
```

> [!IMPORTANT]
> **Explicit Scope Boundary & Deferred Features**:
> **V17 Commit 01 establishes authentication. Authorization and role/permission management are intentionally deferred.**
> 
> Features such as OAuth, Google/Apple/GitHub login, SSO, MFA, WebAuthn/passkeys, password reset email workflows, email verification workflows, session management UI, frontend authentication pages, rate limiting, audit/telemetry platform, and API keys are **not implemented** in this commit and are reserved for future security volumes.

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(auth): implement secure user authentication` | **DONE** |

---

## 3. Authentication Architecture & Boundary Separation

In strict adherence to clean architecture principles:
1. **Zero HTTP Framework Contamination in Domain/Application**:
   `app.modules.identity_access.domain` and `app.modules.identity_access.application` contain **zero imports** of `fastapi`, `starlette`, `HTTPException`, `Request`, or `Response`.
2. **Framework Isolation**:
   Password hashing, token generation/validation, user persistence, and identity resolution are implemented as protocol abstractions (`PasswordHasher`, `TokenService`, `UserRepository`) in domain modules and concrete implementations in infrastructure modules.
3. **Route Handlers as Adapters**:
   FastAPI route functions in `app.api.v1.endpoints.auth` do not contain cryptographic operations or direct database queries; they validate incoming HTTP schemas, delegate to `AuthenticationService` through FastAPI dependencies, and map domain errors to standard HTTP response envelopes.

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
- **Composition**: Arbitrary composition rules (e.g., uppercase + symbol + digit requirements) that degrade entropy without improving security are omitted, following NIST SP 800-63B guidelines.
- **Sanitization**: Plaintext passwords are never logged, never included in exception messages, and never returned in API responses.

---

## 7. Token Design & Configuration

### 7.1 JWT Specifications
- **Format**: Signed JSON Web Tokens (JWT) adhering to RFC 7519.
- **Claims**:
  - `sub`: User ID (UUID string).
  - `email`: Normalized user email.
  - `jti`: Cryptographically random UUID token identifier to ensure token uniqueness.
  - `iat`: Timestamp of issuance (UTC integer).
  - `exp`: Explicit expiration timestamp (UTC integer).
- **Approved Signing Algorithms**: HMAC with SHA-2 (`HS256`, `HS384`, `HS512`). Default: `HS256`.

### 7.2 Configuration & Secrets Management
All cryptographic and authentication settings are managed via environment variables and validated through Pydantic Settings (`app.core.config.Settings`):

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `AUTH_JWT_SECRET` / `REGIMEX_AUTH_JWT_SECRET` | `str` | `""` | Cryptographic HMAC secret. **Mandatory** in production (≥ 32 chars). |
| `AUTH_JWT_ALGORITHM` / `REGIMEX_AUTH_JWT_ALGORITHM` | `str` | `HS256` | Approved HMAC algorithm (`HS256`, `HS384`, `HS512`). |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` / `REGIMEX_AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `60` | Access token lifespan in minutes. Must be > 0. |

> [!CAUTION]
> **Production Guard**:
> In production environments (`ENVIRONMENT=production` or `DEBUG=false`), the application startup fails immediately if `AUTH_JWT_SECRET` is missing, empty, shorter than 32 characters, or contains obvious insecure default strings (`CHANGE_ME`, `secret`, `test`).

---

## 8. Authentication Endpoints & Anti-Enumeration

All authentication routes are mounted under `/api/v1/auth`:

### 8.1 User Registration (`POST /api/v1/auth/register`)
- **Request**: `{"email": "user@example.com", "password": "StrongPassword123!"}`
- **Response** (`201 Created`):
  ```json
  {
    "user": {
      "id": "c1f7a2a0-4b21-4f1e-9a1b-3f4c6e9d7e5b",
      "email": "user@example.com",
      "is_active": true
    }
  }
  ```
- **Duplicate Registration**: Handled with `409 Conflict` backed by the database uniqueness constraint, preventing race condition duplicates without partial records.

### 8.2 User Login (`POST /api/v1/auth/login`)
- **Request**: `{"email": "user@example.com", "password": "StrongPassword123!"}`
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "c1f7a2a0-4b21-4f1e-9a1b-3f4c6e9d7e5b",
      "email": "user@example.com",
      "is_active": true
    }
  }
  ```
- **Anti-Enumeration Protection**:
  When an unknown email is supplied, the authentication service executes a constant-time dummy Argon2id verification. Both unknown email and incorrect password yield the exact same public error response (`401 Unauthorized` with `INVALID_CREDENTIALS` code), mitigating timing attacks and account enumeration.

### 8.3 Current User Resolution (`GET /api/v1/auth/me`)
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`200 OK`):
  ```json
  {
    "id": "c1f7a2a0-4b21-4f1e-9a1b-3f4c6e9d7e5b",
    "email": "user@example.com",
    "is_active": true
  }
  ```
- **Security**: Protected by the `CurrentUser` FastAPI dependency. Requires a valid, unexpired token whose subject resolves to an active user in the database.

---

## 9. Error Contract & Mapping

All authentication errors map directly into the standard RegimeX `ApiError` envelope:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password.",
    "request_id": "951244c9-84a3-43e2-aba8-c2d038a0c51e",
    "details": null
  }
}
```

| Domain Error | HTTP Status | Error Code | Description |
| :--- | :---: | :--- | :--- |
| `AuthenticationRequiredError` | `401` | `AUTHENTICATION_REQUIRED` | Missing or invalid Authorization header scheme. |
| `InvalidTokenError` | `401` | `AUTHENTICATION_REQUIRED` | Malformed or invalid JWT signature. |
| `ExpiredTokenError` | `401` | `AUTHENTICATION_REQUIRED` | Expired access token. |
| `InvalidCredentialsError` | `401` | `INVALID_CREDENTIALS` | Invalid email or incorrect password (anti-enumeration). |
| `InactiveUserError` | `401` | `ACCOUNT_INACTIVE` | Account deactivated by administrative action. |
| `DuplicateEmailError` | `409` | `DUPLICATE_EMAIL` | Account with normalized email already exists. |
| `InvalidPasswordError` | `422` | `INVALID_PASSWORD` | Password does not meet 12-character minimum policy. |
| `InvalidEmailError` | `422` | `INVALID_EMAIL` | Email format is invalid or exceeds length bounds. |

---

## 10. Database Migration

Migration `0002_create_users_table.py` was created using Alembic:
- Establishes the `users` table with primary key `id`, normalized `email`, `password_hash`, `is_active`, and timezone-aware timestamps.
- Creates unique constraint `uq_users_email` and index `ix_users_email`.
- Supports bidirectional migration execution (`upgrade` and `downgrade`).

---

## 11. Verification & Quality Gates

The authentication platform has been subjected to rigorous automated verification:

| Gate | Command | Result |
| :--- | :--- | :---: |
| **Pytest Full Suite** | `python -m pytest -q` | **PASS (1,246 passed, 1 skipped)** |
| **API & Auth Tests** | `python -m pytest -v tests/api/` | **PASS (88 passed)** |
| **Unit Auth Tests** | `python -m pytest -v tests/unit/identity_access/` | **PASS (41 passed)** |
| **Ruff Linter** | `python -m ruff check app tests` | **PASS (0 warnings)** |
| **Ruff Formatter** | `python -m ruff format --check app tests` | **PASS (350 files clean)** |
| **Mypy Static Typing** | `python -m mypy app tests` | **PASS (350 source files)** |
| **Frontend Lint** | `npm run lint` (apps/web) | **PASS (0 warnings, 0 errors)** |
| **Frontend Type-Check** | `npm run type-check` (apps/web) | **PASS (clean)** |
| **Alembic Migration** | `alembic upgrade head && alembic downgrade -1` | **PASS (clean)** |
