"""
Integration and Architecture Tests for API Security Hardening & Boundaries.
===========================================================================
Verifies:
1. Standard Security Headers (nosniff, frame denial, referrer policy, CSP, Permissions-Policy).
2. Conditional HSTS (Strict-Transport-Security over HTTPS / production, never on local HTTP).
3. Request ID sanitization (bounding length, rejecting CRLF injection, generating UUID4 fallback).
4. Request payload boundaries (Content-Length limits, rejecting oversized payloads with HTTP 413).
5. CORS hardening (explicit allowed origins, wildcard rejection in production).
6. Authorization boundary enforcement (inactive user rejected, valid user permitted).
7. JWT cryptographic hardening (algorithm allowlist, non-UUID subject rejection, exp > iat check).
8. Secrets isolation (passwords, JWT secrets, and database credentials are never leaked).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import jwt
import pytest
from app.core.config import Environment, Settings
from app.core.dependencies import get_current_user
from app.main import create_app
from app.modules.identity_access.application.dto import UserDTO
from fastapi.testclient import TestClient


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestSecurityHeaders:
    def test_baseline_security_headers_present(self, api_client: TestClient) -> None:
        """Verify nosniff, frame options, referrer, and permissions headers on all responses."""
        res = api_client.get("/health")
        assert res.status_code == 200
        headers = res.headers

        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in headers.get("permissions-policy", "")
        assert "microphone=()" in headers.get("permissions-policy", "")

    def test_content_security_policy_on_api_endpoints(self, api_client: TestClient) -> None:
        """Verify strict CSP is attached to API endpoints."""
        res = api_client.get("/api/v1/markets")
        csp = res.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_not_present_on_plain_http_development(self, api_client: TestClient) -> None:
        """Verify Strict-Transport-Security is NOT emitted during plain local HTTP development."""
        res = api_client.get("/health")
        assert "strict-transport-security" not in res.headers

    def test_hsts_present_over_https(self, api_client: TestClient) -> None:
        """Verify Strict-Transport-Security is attached when request is served over HTTPS."""
        res = api_client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert "strict-transport-security" in res.headers
        hsts = res.headers["strict-transport-security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts


class TestRequestIdHardening:
    def test_safe_request_id_preserved(self, api_client: TestClient) -> None:
        """Valid client-provided correlation ID is echoed verbatim."""
        safe_id = "trace-req-123456"
        res = api_client.get("/health", headers={"X-Request-ID": safe_id})
        assert res.headers.get("x-request-id") == safe_id

    def test_oversized_request_id_discarded_and_replaced(self, api_client: TestClient) -> None:
        """An oversized X-Request-ID (>64 chars) is discarded and replaced with a valid UUID."""
        oversized_id = "A" * 128
        res = api_client.get("/health", headers={"X-Request-ID": oversized_id})
        echoed_id = res.headers.get("x-request-id")
        assert echoed_id != oversized_id
        # Verify it was replaced by a valid UUID
        uuid.UUID(echoed_id)

    def test_malicious_crlf_request_id_sanitized(self, api_client: TestClient) -> None:
        """Header-injection attempt containing CRLF / special characters is sanitized."""
        malicious_id = "test\r\nX-Injected: evil"
        res = api_client.get("/health", headers={"X-Request-ID": malicious_id})
        echoed_id = res.headers.get("x-request-id")
        assert "\r" not in echoed_id
        assert "\n" not in echoed_id
        assert "Injected" not in echoed_id
        uuid.UUID(echoed_id)


class TestRequestBoundaryProtection:
    def test_oversized_payload_rejected_with_413(self, api_client: TestClient) -> None:
        """Verify request with Content-Length exceeding configured maximum returns HTTP 413."""
        excessive_length = 50 * 1024 * 1024  # 50MB
        res = api_client.post(
            "/api/v1/auth/register",
            content=b"{}",
            headers={"Content-Length": str(excessive_length)},
        )
        assert res.status_code == 413
        body = res.json()
        assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_invalid_content_length_rejected_with_400(self, api_client: TestClient) -> None:
        """Verify malformed Content-Length header returns HTTP 400."""
        res = api_client.post(
            "/api/v1/auth/register",
            content=b"{}",
            headers={"Content-Length": "not-a-number"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"

    def test_negative_content_length_rejected_with_400(self, api_client: TestClient) -> None:
        """Verify negative Content-Length header returns HTTP 400."""
        res = api_client.post(
            "/api/v1/auth/register",
            content=b"{}",
            headers={"Content-Length": "-100"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"


class TestCorsHardening:
    def test_allowed_origin_receives_cors_header(self, api_client: TestClient) -> None:
        """Requests from configured origin receive Access-Control-Allow-Origin."""
        res = api_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_does_not_receive_cors_header(self, api_client: TestClient) -> None:
        """Requests from unauthorized origin do not receive Access-Control-Allow-Origin."""
        res = api_client.get(
            "/health",
            headers={"Origin": "http://malicious-site.example"},
        )
        assert res.headers.get("access-control-allow-origin") is None

    def test_production_rejects_wildcard_cors_origin(self) -> None:
        """Production configuration must reject wildcard '*' origin."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="A" * 32,
                allowed_origins=["*"],
            )
        assert "Wildcard '*' CORS origins are strictly prohibited" in str(exc_info.value)


class TestAuthorizationBoundary:
    def test_inactive_user_rejected_at_boundary(self) -> None:
        """Inactive user is rejected with HTTP 401 at the authorization boundary."""
        app = create_app()
        inactive_user = UserDTO(
            id=uuid.uuid4(),
            email="inactive.analyst@regimex.org",
            is_active=False,
            created_at=datetime.now(tz=UTC),
        )
        app.dependency_overrides[get_current_user] = lambda: inactive_user

        with TestClient(app) as client:
            res = client.get("/api/v1/auth/me")
            assert res.status_code == 401
            assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_active_user_permitted_at_boundary(self) -> None:
        """Active user is permitted and resolves identity at the authorization boundary."""
        app = create_app()
        active_user = UserDTO(
            id=uuid.uuid4(),
            email="active.analyst@regimex.org",
            is_active=True,
            created_at=datetime.now(tz=UTC),
        )
        app.dependency_overrides[get_current_user] = lambda: active_user

        with TestClient(app) as client:
            res = client.get("/api/v1/auth/me")
            assert res.status_code == 200
            assert res.json()["email"] == "active.analyst@regimex.org"


class TestJwtSecurityHardening:
    def test_token_with_non_uuid_sub_rejected(self, api_client: TestClient) -> None:
        """Token with subject that is not a valid UUID string is rejected with 401."""
        test_secret = "test-secret-key-not-for-production-use"
        payload = {
            "sub": "not-a-valid-uuid",
            "email": "user@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, test_secret, algorithm="HS256")
        res = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_token_with_exp_before_iat_rejected(self, api_client: TestClient) -> None:
        """Token with exp <= iat is rejected with 401."""
        test_secret = "test-secret-key-not-for-production-use"
        now_ts = int(time.time())
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "user@regimex.org",
            "iat": now_ts,
            "exp": now_ts - 10,
        }
        token = jwt.encode(payload, test_secret, algorithm="HS256")
        res = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401


class TestSecretIsolation:
    def test_root_endpoint_does_not_expose_secrets(self, api_client: TestClient) -> None:
        """GET / must never expose secret keys or connection strings."""
        res = api_client.get("/")
        content = res.text
        assert "CHANGE_ME" not in content
        assert "postgresql" not in content
        assert "secret" not in content.lower()

    def test_health_and_ready_do_not_expose_secrets(self, api_client: TestClient) -> None:
        """Diagnostic probes must never reveal secrets."""
        for path in ("/health", "/ready"):
            res = api_client.get(path)
            content = res.text
            assert "CHANGE_ME" not in content
            assert "postgresql" not in content

    def test_openapi_schema_does_not_contain_secrets(self, api_client: TestClient) -> None:
        """GET /openapi.json must never contain secret keys or database credentials."""
        res = api_client.get("/openapi.json")
        content = res.text
        assert "CHANGE_ME" not in content
        assert "changeme" not in content
