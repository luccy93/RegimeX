"""
Unit tests for JWT access token service.
========================================
Verifies token creation, signing, claim validation, expiration handling,
signature verification, algorithm restriction, and malformed token rejection.
"""

from __future__ import annotations

import time
import uuid

import jwt
import pytest
from app.modules.identity_access.domain.errors import (
    ExpiredTokenError,
    InvalidTokenError,
)
from app.modules.identity_access.domain.token import TokenService
from app.modules.identity_access.infrastructure.security.token import (
    JwtTokenService,
)

TEST_SECRET = "test-secret-key-32-bytes-minimum-length-for-hmac-sha256"


class TestJwtTokenService:
    def test_create_and_decode_valid_token(self, token_service: TokenService) -> None:
        """Verify standard lifecycle: create token and decode claims successfully."""
        user_id = str(uuid.uuid4())
        email = "analyst@regimex.org"

        token = token_service.create_access_token(subject=user_id, email=email)
        assert isinstance(token, str)
        assert len(token) > 20

        claims = token_service.decode_access_token(token)
        assert claims.sub == user_id
        assert claims.email == email
        assert claims.jti is not None
        assert claims.exp > claims.iat

    def test_token_contains_expected_claims(self, token_service: TokenService) -> None:
        """Verify claims include sub, email, iat, exp, and jti."""
        user_id = str(uuid.uuid4())
        email = "claims.test@regimex.org"

        token = token_service.create_access_token(subject=user_id, email=email)
        claims = token_service.decode_access_token(token)

        assert claims.sub == user_id
        assert claims.email == email
        assert isinstance(claims.jti, str)

    def test_expired_token_raises_expired_token_error(self) -> None:
        """Verify that an expired token raises ExpiredTokenError."""
        service = JwtTokenService(secret=TEST_SECRET, expire_minutes=60)
        user_id = str(uuid.uuid4())

        # Construct expired payload manually
        past_time = int(time.time()) - 100
        expired_payload = {
            "sub": user_id,
            "email": "expired@regimex.org",
            "iat": past_time - 3600,
            "exp": past_time,
            "jti": str(uuid.uuid4()),
        }
        expired_token = jwt.encode(expired_payload, TEST_SECRET, algorithm="HS256")

        with pytest.raises(ExpiredTokenError):
            service.decode_access_token(expired_token)

    def test_invalid_signature_raises_invalid_token_error(self) -> None:
        """Verify token signed with a different key is rejected."""
        service = JwtTokenService(secret=TEST_SECRET)
        wrong_secret = "completely-different-signing-key-for-testing-purposes"
        user_id = str(uuid.uuid4())

        now_ts = int(time.time())
        wrong_key_token = jwt.encode(
            {
                "sub": user_id,
                "email": "hacker@test.com",
                "iat": now_ts,
                "exp": now_ts + 3600,
            },
            wrong_secret,
            algorithm="HS256",
        )

        with pytest.raises(InvalidTokenError):
            service.decode_access_token(wrong_key_token)

    def test_malformed_token_string_raises_invalid_token_error(
        self, token_service: TokenService
    ) -> None:
        """Verify non-JWT malformed string raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            token_service.decode_access_token("this.is.not.a.valid.jwt.token")

        with pytest.raises(InvalidTokenError):
            token_service.decode_access_token("garbage")

    def test_empty_token_raises_invalid_token_error(self, token_service: TokenService) -> None:
        """Verify empty token string raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            token_service.decode_access_token("")

        with pytest.raises(InvalidTokenError):
            token_service.decode_access_token("   ")

    def test_missing_subject_claim_raises_invalid_token_error(self) -> None:
        """Verify token missing 'sub' claim is rejected."""
        service = JwtTokenService(secret=TEST_SECRET)
        payload = {
            "email": "nosub@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token_without_sub = jwt.encode(payload, TEST_SECRET, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            service.decode_access_token(token_without_sub)

    def test_insecure_none_algorithm_rejected_at_initialization(self) -> None:
        """Verify 'none' algorithm is rejected."""
        with pytest.raises(ValueError) as exc_info:
            JwtTokenService(secret=TEST_SECRET, algorithm="none")
        assert "Unsupported JWT algorithm" in str(exc_info.value)

    def test_empty_secret_rejected_at_initialization(self) -> None:
        """Verify empty secret is rejected."""
        with pytest.raises(ValueError):
            JwtTokenService(secret="")

    def test_invalid_expiration_rejected_at_initialization(self) -> None:
        """Verify non-positive expiration is rejected."""
        with pytest.raises(ValueError):
            JwtTokenService(secret=TEST_SECRET, expire_minutes=0)
        with pytest.raises(ValueError):
            JwtTokenService(secret=TEST_SECRET, expire_minutes=-10)

    def test_negative_leeway_rejected_at_initialization(self) -> None:
        """Verify negative leeway seconds is rejected."""
        with pytest.raises(ValueError) as exc_info:
            JwtTokenService(secret=TEST_SECRET, leeway_seconds=-1)
        assert "Leeway seconds cannot be negative" in str(exc_info.value)

    def test_invalid_uuid_subject_raises_invalid_token_error(self) -> None:
        """Verify token with non-UUID 'sub' claim is rejected."""
        service = JwtTokenService(secret=TEST_SECRET)
        payload = {
            "sub": "not-a-valid-uuid-format",
            "email": "badsub@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token_bad_sub = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(InvalidTokenError) as exc_info:
            service.decode_access_token(token_bad_sub)
        assert "valid UUID" in str(exc_info.value)

    def test_exp_less_than_or_equal_to_iat_rejected(self) -> None:
        """Verify token with exp <= iat is rejected as invalid."""
        service = JwtTokenService(secret=TEST_SECRET)
        future_ts = int(time.time()) + 3600
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "clockskew@regimex.org",
            "iat": future_ts + 100,  # iat after exp
            "exp": future_ts,
        }
        token_skewed_timestamps = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            service.decode_access_token(token_skewed_timestamps)

    def test_issuer_validation_success_and_mismatch(self) -> None:
        """Verify configured issuer requirement validates matching tokens and rejects mismatch."""
        service = JwtTokenService(secret=TEST_SECRET, issuer="regimex-auth-service")
        user_id = str(uuid.uuid4())

        # Matching issuer
        token = service.create_access_token(subject=user_id, email="issuer@regimex.org")
        claims = service.decode_access_token(token)
        assert claims.iss == "regimex-auth-service"

        # Mismatched issuer
        mismatched_payload = {
            "sub": user_id,
            "email": "attacker@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "rogue-issuer",
        }
        mismatched_token = jwt.encode(mismatched_payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            service.decode_access_token(mismatched_token)

        # Missing issuer when configured
        no_iss_payload = {
            "sub": user_id,
            "email": "noiss@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        no_iss_token = jwt.encode(no_iss_payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            service.decode_access_token(no_iss_token)

    def test_audience_validation_success_and_mismatch(self) -> None:
        """Verify configured audience requirement validates matching tokens and rejects mismatch."""
        service = JwtTokenService(secret=TEST_SECRET, audience="regimex-api-client")
        user_id = str(uuid.uuid4())

        # Matching audience
        token = service.create_access_token(subject=user_id, email="audience@regimex.org")
        claims = service.decode_access_token(token)
        assert claims.aud == "regimex-api-client"

        # Mismatched audience
        mismatched_payload = {
            "sub": user_id,
            "email": "attacker@regimex.org",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "aud": "rogue-audience",
        }
        mismatched_token = jwt.encode(mismatched_payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            service.decode_access_token(mismatched_token)
