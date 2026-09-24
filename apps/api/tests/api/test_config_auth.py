"""
Unit tests for Authentication and Security Configuration.
==========================================================
Verifies:
1. Production secret key validation (rejects missing, empty, short, or placeholder secrets).
2. Development/test environments allow safe defaults.
3. Insecure/unsupported JWT algorithms are rejected.
4. Environment variable aliases (AUTH_JWT_SECRET, AUTH_JWT_ALGORITHM, etc.) are respected.
"""

from __future__ import annotations

import pytest
from app.core.config import Environment, Settings


class TestAuthConfigValidation:
    def test_development_and_test_allow_safe_defaults(self) -> None:
        """Verify development and test environments instantiate settings with defaults."""
        dev_settings = Settings(env=Environment.DEVELOPMENT)
        assert dev_settings.is_development is True
        assert dev_settings.jwt_algorithm == "HS256"
        assert dev_settings.auth_jwt_secret is not None

        test_settings = Settings(env=Environment.TEST)
        assert test_settings.is_test is True

    def test_production_rejects_default_placeholder_secret(self) -> None:
        """Verify production environment fails fast if default placeholder secret is used."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="CHANGE_ME_in_production_use_32+_random_bytes",
            )
        assert "secure random value" in str(exc_info.value)

    def test_production_rejects_empty_secret(self) -> None:
        """Verify production environment fails fast if secret is empty or whitespace."""
        with pytest.raises(ValueError):
            Settings(
                env=Environment.PRODUCTION,
                secret_key="",
            )

        with pytest.raises(ValueError):
            Settings(
                env=Environment.PRODUCTION,
                secret_key="   ",
            )

    def test_production_rejects_short_secret(self) -> None:
        """Verify production environment rejects secret keys shorter than 32 characters."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="too-short-secret-key-12345",
            )
        assert "at least 32 characters" in str(exc_info.value)

    def test_production_accepts_strong_secret(self) -> None:
        """Verify production accepts valid 32+ character secret."""
        strong_secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        prod_settings = Settings(
            env=Environment.PRODUCTION,
            secret_key=strong_secret,
        )
        assert prod_settings.auth_jwt_secret == strong_secret

    def test_insecure_none_algorithm_rejected(self) -> None:
        """Verify algorithm 'none' is rejected."""
        with pytest.raises(ValueError) as exc_info:
            Settings(jwt_algorithm="none")
        assert "Unsupported or insecure JWT algorithm" in str(exc_info.value)

    def test_unsupported_algorithm_rejected(self) -> None:
        """Verify arbitrary algorithm is rejected."""
        with pytest.raises(ValueError):
            Settings(jwt_algorithm="UNSUPPORTED_ALGO")

    def test_supported_hmac_algorithms_accepted(self) -> None:
        """Verify approved HMAC algorithms (HS256, HS384, HS512) are accepted."""
        for algo in ["HS256", "HS384", "HS512", "hs256", "hs512"]:
            settings = Settings(jwt_algorithm=algo)
            assert settings.jwt_algorithm == algo.upper()

    def test_environment_variable_aliases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify AUTH_JWT_* aliases map to settings correctly."""
        monkeypatch.setenv("AUTH_JWT_SECRET", "custom-secret-key-that-is-long-enough-32-chars")
        monkeypatch.setenv("AUTH_JWT_ALGORITHM", "HS384")
        monkeypatch.setenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "120")

        settings = Settings()
        assert settings.auth_jwt_secret == "custom-secret-key-that-is-long-enough-32-chars"
        assert settings.auth_jwt_algorithm == "HS384"
        assert settings.auth_access_token_expire_minutes == 120
