"""
RegimeX Identity & Access — JWT Token Service
=============================================
Concrete implementation of TokenService protocol using PyJWT.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import InvalidTokenError as PyJWTInvalidTokenError

from app.modules.identity_access.domain.errors import (
    ExpiredTokenError,
    InvalidTokenError,
)
from app.modules.identity_access.domain.models import TokenClaims
from app.modules.identity_access.domain.token import TokenService

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = {"HS256", "HS384", "HS512"}


class JwtTokenService(TokenService):
    """
    Stateless JWT token signing and verification service.

    Adheres to cryptographic standards:
    - Enforces approved symmetric HMAC algorithms (HS256, HS384, HS512).
    - Requires non-empty, strong signing secret.
    - Validates mandatory claims: sub, exp, iat, jti.
    - Emits timezone-aware UTC timestamps.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        expire_minutes: int = 60,
        issuer: str | None = None,
        audience: str | None = None,
        leeway_seconds: int = 0,
    ) -> None:
        if not secret or not secret.strip():
            raise ValueError("JWT signing secret cannot be empty.")

        algo_upper = algorithm.upper()
        if algo_upper not in ALLOWED_ALGORITHMS:
            allowed = sorted(ALLOWED_ALGORITHMS)
            msg = f"Unsupported JWT algorithm '{algorithm}'. Must be one of {allowed}"
            raise ValueError(msg)

        if expire_minutes <= 0:
            raise ValueError("Access token expiration minutes must be greater than zero.")

        if leeway_seconds < 0:
            raise ValueError("Leeway seconds cannot be negative.")

        self._secret = secret
        self._algorithm = algo_upper
        self._expire_minutes = expire_minutes
        self._issuer = issuer.strip() if issuer and issuer.strip() else None
        self._audience = audience.strip() if audience and audience.strip() else None
        self._leeway_seconds = leeway_seconds

    def create_access_token(self, subject: str, email: str) -> str:
        """
        Create a signed, short-lived JWT access token for a subject.

        Payload claims:
          - sub: Subject user UUID string
          - email: Canonical user email
          - iat: Issued at timestamp (seconds)
          - exp: Expiration timestamp (seconds)
          - jti: Unique token identifier
          - iss: Issuer identifier (if configured)
          - aud: Audience identifier (if configured)
        """
        if not subject:
            raise ValueError("Subject identifier cannot be empty.")
        if not email:
            raise ValueError("User email cannot be empty.")

        now = datetime.now(tz=UTC)
        exp = now + timedelta(minutes=self._expire_minutes)
        token_id = str(uuid.uuid4())

        payload: dict[str, Any] = {
            "sub": subject,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": token_id,
        }

        if self._issuer is not None:
            payload["iss"] = self._issuer
        if self._audience is not None:
            payload["aud"] = self._audience

        return jwt.encode(
            payload=payload,
            key=self._secret,
            algorithm=self._algorithm,
        )

    def decode_access_token(self, token: str) -> TokenClaims:
        """
        Decode and validate a signed JWT access token.

        Enforces:
          - Cryptographic signature check with configured secret and allowed algorithm.
          - Rejection of 'none' algorithm and unauthorized algorithms.
          - Mandatory claims: sub, exp, iat.
          - exp > iat validation.
          - Valid UUID subject check.
          - Issuer and audience verification when configured.

        Raises:
            ExpiredTokenError: If the token is expired.
            InvalidTokenError: If signature, claims, or format are invalid.
        """
        if not token or not token.strip():
            raise InvalidTokenError("Authentication token cannot be empty.")

        decode_options: dict[str, Any] = {
            "require": ["sub", "exp", "iat"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
        }
        decode_kwargs: dict[str, Any] = {
            "jwt": token.strip(),
            "key": self._secret,
            "algorithms": [self._algorithm],
            "options": decode_options,
            "leeway": self._leeway_seconds,
        }

        if self._issuer is not None:
            decode_options["verify_iss"] = True
            decode_kwargs["issuer"] = self._issuer
        if self._audience is not None:
            decode_options["verify_aud"] = True
            decode_kwargs["audience"] = self._audience

        try:
            payload = jwt.decode(**decode_kwargs)
        except ExpiredSignatureError as e:
            raise ExpiredTokenError("Authentication token has expired.") from e
        except (
            jwt.InvalidIssuerError,
            jwt.InvalidAudienceError,
            jwt.InvalidAlgorithmError,
            jwt.MissingRequiredClaimError,
            PyJWTInvalidTokenError,
        ) as e:
            raise InvalidTokenError(f"Invalid authentication token: {e}") from e
        except Exception as e:
            logger.warning("Unexpected error decoding token: %s", type(e).__name__)
            raise InvalidTokenError("Malformed or undecodable authentication token.") from e

        sub = payload.get("sub")
        if not sub or not isinstance(sub, str):
            raise InvalidTokenError("Token 'sub' claim must be a non-empty string.")

        try:
            uuid.UUID(sub)
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidTokenError("Token 'sub' claim must be a valid UUID string.") from exc

        iat_raw = payload.get("iat")
        exp_raw = payload.get("exp")
        if not isinstance(iat_raw, (int, float)) or not isinstance(exp_raw, (int, float)):
            raise InvalidTokenError("Token timestamps 'iat' and 'exp' must be numeric.")

        if exp_raw <= iat_raw:
            raise InvalidTokenError(
                "Token expiration ('exp') must be strictly greater than issue time ('iat')."
            )

        email = payload.get("email", "")
        jti = payload.get("jti") or str(uuid.uuid4())

        iat = datetime.fromtimestamp(iat_raw, tz=UTC)
        exp = datetime.fromtimestamp(exp_raw, tz=UTC)

        return TokenClaims(
            sub=str(sub),
            email=str(email),
            iat=iat,
            exp=exp,
            jti=str(jti),
            iss=payload.get("iss"),
            aud=payload.get("aud"),
        )
