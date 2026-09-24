"""
Unit tests for canonical email normalization.
=============================================
Verifies trimming of whitespace, lowercase conversion, format validation,
and rejection of invalid or malformed email addresses.
"""

from __future__ import annotations

import pytest
from app.modules.identity_access.domain.errors import InvalidEmailError
from app.modules.identity_access.domain.services import normalize_email


class TestEmailNormalization:
    def test_trims_leading_and_trailing_whitespace(self) -> None:
        """Verify leading and trailing whitespace is stripped."""
        assert normalize_email("  user@example.com  ") == "user@example.com"
        assert normalize_email("\tuser@example.com\n") == "user@example.com"

    def test_converts_to_lowercase(self) -> None:
        """Verify email is converted to canonical lowercase."""
        assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"
        assert normalize_email("User.Name+Tag@Sub.Domain.ORG") == "user.name+tag@sub.domain.org"

    def test_combined_whitespace_and_case_normalization(self) -> None:
        """Verify combined normalization is deterministic."""
        assert normalize_email("  QuantResearcher@RegimeX.AI  ") == "quantresearcher@regimex.ai"

    def test_valid_emails_pass(self) -> None:
        """Verify standard valid email formats succeed."""
        valid_emails = [
            "trader@hedgefund.com",
            "first.last@company.co.uk",
            "user+filter@domain.io",
            "researcher_123@sub.domain.org",
        ]
        for email in valid_emails:
            assert normalize_email(email) == email.lower()

    def test_empty_and_blank_emails_rejected(self) -> None:
        """Verify empty and whitespace-only emails raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            normalize_email("")
        with pytest.raises(InvalidEmailError):
            normalize_email("   ")
        with pytest.raises(InvalidEmailError):
            normalize_email("\t\n")

    def test_malformed_emails_rejected(self) -> None:
        """Verify malformed email formats raise InvalidEmailError."""
        invalid_emails = [
            "plainaddress",
            "@missingusername.com",
            "missingdomain@",
            "username@.com",
            "username@com",
            "username space@domain.com",
            "user@@domain.com",
        ]
        for email in invalid_emails:
            with pytest.raises(InvalidEmailError):
                normalize_email(email)
