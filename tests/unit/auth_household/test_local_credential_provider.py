"""
Unit tests for LocalCredentialProvider.

Scenario: verify_identity with email + bcrypt password.
All tests mock UserRepository — no database touched.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.auth_household.utils.oidc_provider import (
    IdentityClaim,
    LocalCredentialProvider,
)
from app.shared.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email: str = "alice@example.com", password: str = "secret") -> MagicMock:
    """Return a minimal mock User with a real bcrypt hash."""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.full_name = "Alice Example"
    user.password_hash = pwd_context.hash(password)
    user.is_active = True
    return user


def _make_provider(user_or_none) -> LocalCredentialProvider:
    repo = AsyncMock()
    repo.get_by_email.return_value = user_or_none
    return LocalCredentialProvider(user_repo=repo)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGivenValidCredentials:
    async def test_when_verify_then_returns_identity_claim(self):
        """
        Scenario: correct email + password
        Given: user exists with matching bcrypt hash
        When: verify_identity is called with correct credentials
        Then: an IdentityClaim with the correct sub, email, name is returned
        """
        user = _make_user(email="alice@example.com", password="correct-pass")
        provider = _make_provider(user)

        result = await provider.verify_identity(
            email="alice@example.com", password="correct-pass"
        )

        assert isinstance(result, IdentityClaim)
        assert result.sub == str(user.id)
        assert result.email == "alice@example.com"
        assert result.name == "Alice Example"
        assert result.email_verified is False

    async def test_when_verify_then_email_verified_is_always_false(self):
        """Phase 1: email_verified is always False — set by providers in Phase 2."""
        user = _make_user(password="pw")
        provider = _make_provider(user)

        result = await provider.verify_identity(email=user.email, password="pw")

        assert result.email_verified is False


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------


class TestGivenWrongPassword:
    async def test_when_verify_then_raises_authentication_error(self):
        """
        Scenario: user exists but password is wrong
        Given: user record found in DB
        When: verify_identity called with incorrect password
        Then: AuthenticationError is raised
        """
        user = _make_user(password="correct")
        provider = _make_provider(user)

        with pytest.raises(AuthenticationError):
            await provider.verify_identity(email=user.email, password="wrong")

    async def test_when_verify_then_error_message_is_generic(self):
        """No credential enumeration — message must not reveal which field was wrong."""
        user = _make_user(password="correct")
        provider = _make_provider(user)

        with pytest.raises(AuthenticationError) as exc_info:
            await provider.verify_identity(email=user.email, password="wrong")

        assert exc_info.value.args[0] == "Invalid credentials"


# ---------------------------------------------------------------------------
# Unknown email — timing-safe
# ---------------------------------------------------------------------------


class TestGivenUnknownEmail:
    async def test_when_verify_then_raises_authentication_error(self):
        """
        Scenario: email not in DB
        Given: UserRepository.get_by_email returns None
        When: verify_identity is called
        Then: AuthenticationError is raised (same as wrong password)
        """
        provider = _make_provider(None)

        with pytest.raises(AuthenticationError):
            await provider.verify_identity(
                email="nobody@example.com", password="anything"
            )

    async def test_when_verify_then_dummy_bcrypt_runs_for_timing_safety(self):
        """
        Timing-safe: even when the user is not found, we still call
        pwd_context.verify with a dummy hash to prevent timing-based enumeration.
        """
        provider = _make_provider(None)

        with (
            patch(
                "app.modules.auth_household.utils.oidc_provider.pwd_context.verify",
                return_value=False,
            ) as mock_verify,
            pytest.raises(AuthenticationError),
        ):
            await provider.verify_identity(
                email="ghost@example.com", password="anything"
            )

        mock_verify.assert_called_once()

    async def test_error_message_matches_wrong_password_message(self):
        """Both failure paths must produce identical error messages (no enumeration)."""
        provider_unknown = _make_provider(None)
        user = _make_user(password="real")
        provider_wrong = _make_provider(user)

        with pytest.raises(AuthenticationError) as no_user_exc:
            await provider_unknown.verify_identity(email="x@x.com", password="y")

        with pytest.raises(AuthenticationError) as wrong_pass_exc:
            await provider_wrong.verify_identity(email=user.email, password="bad")

        assert no_user_exc.value.args[0] == wrong_pass_exc.value.args[0]
