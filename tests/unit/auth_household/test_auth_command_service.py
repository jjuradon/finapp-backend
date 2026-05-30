"""
Unit tests for AuthCommandService.

All external dependencies (repositories, Redis, OIDCProvider) are mocked.
No database or network calls — pure business logic verification.
"""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.auth_household.schemas.auth import (
    CompleteAuthSchema,
    RegisterSchema,
    TokenRequestParams,
)
from app.modules.auth_household.services.auth_command_service import AuthCommandService
from app.shared.exceptions import (
    AuthenticationError,
    ConflictError,
)

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _make_user(role: str = "owner") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.full_name = "Alice"
    user.is_active = True
    user.email_verified = False
    return user


def _make_membership(user_id, household_id, role: str = "owner") -> MagicMock:
    m = MagicMock()
    m.household_id = household_id
    m.user_id = user_id
    m.role = role
    return m


def _make_service(
    user_repo=None,
    household_repo=None,
    hm_repo=None,
    code_repo=None,
    rt_repo=None,
    provider=None,
    redis=None,
    client_registry=None,
    token_service=None,
    rate_limiter=None,
) -> AuthCommandService:
    return AuthCommandService(
        user_repo=user_repo or AsyncMock(),
        household_repo=household_repo or AsyncMock(),
        household_member_repo=hm_repo or AsyncMock(),
        code_repo=code_repo or AsyncMock(),
        refresh_token_repo=rt_repo or AsyncMock(),
        provider=provider or AsyncMock(),
        redis=redis or AsyncMock(),
        client_registry=client_registry or MagicMock(),
        token_service=token_service or MagicMock(),
        rate_limiter=rate_limiter or AsyncMock(),
    )


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


class TestGivenValidPayloadWhenRegister:
    async def test_then_creates_user_household_member(self):
        """
        Scenario: new user registration
        Given: valid RegisterSchema with unique email
        When: register() is called
        Then: UserRepository.create, HouseholdRepository.create, and
              HouseholdMemberRepository.create are all called exactly once
        """
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None  # email not taken
        user_repo.create.return_value = _make_user()

        hh_repo = AsyncMock()
        hm_repo = AsyncMock()

        svc = _make_service(
            user_repo=user_repo, household_repo=hh_repo, hm_repo=hm_repo
        )

        payload = RegisterSchema(
            email="new@example.com",
            password="password123",
            full_name="New User",
            household_name="My Home",
        )
        await svc.register(payload)

        user_repo.create.assert_called_once()
        hh_repo.create.assert_called_once()
        hm_repo.create.assert_called_once()

    async def test_then_returns_user_created_schema(self):
        user = _make_user()
        household_id = uuid.uuid4()

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None
        user_repo.create.return_value = user

        hh_repo = AsyncMock()
        created_hh = MagicMock()
        created_hh.id = household_id
        hh_repo.create.return_value = created_hh

        hm_repo = AsyncMock()

        svc = _make_service(
            user_repo=user_repo, household_repo=hh_repo, hm_repo=hm_repo
        )
        payload = RegisterSchema(
            email="a@b.com",
            password="password123",
            full_name="A B",
            household_name="Home",
        )

        result = await svc.register(payload)

        assert result.user_id == user.id
        assert result.email == user.email
        assert result.role == "owner"


class TestGivenDuplicateEmailWhenRegister:
    async def test_then_raises_conflict_error(self):
        """
        Scenario: email already registered
        Given: UserRepository.get_by_email returns an existing user
        When: register() is called with that email
        Then: ConflictError is raised
        """
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = _make_user()

        svc = _make_service(user_repo=user_repo)

        with pytest.raises(ConflictError):
            await svc.register(
                RegisterSchema(
                    email="taken@example.com",
                    password="password123",
                    full_name="X",
                    household_name="Y",
                )
            )

        # create must NOT have been called
        user_repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# start_authorization()
# ---------------------------------------------------------------------------


class TestGivenValidParamsWhenStartAuthorization:
    async def test_then_stores_pkce_state_in_redis(self):
        """
        Scenario: PKCE authorize step
        Given: valid client_id and redirect_uri registered with OIDCClientRegistry
        When: start_authorization() is called
        Then: Redis is called with the PKCE state key and a TTL
        """
        verifier, challenge = _pkce_pair()

        client_registry = MagicMock()
        client_registry.get_client.return_value = MagicMock(
            client_id="finapp-web",
            redirect_uris=["http://localhost:5173/auth/callback"],
        )
        client_registry.validate_redirect_uri.return_value = True

        redis = AsyncMock()
        redis.setex = AsyncMock()

        svc = _make_service(client_registry=client_registry, redis=redis)

        from app.modules.auth_household.schemas.auth import AuthorizeParams

        params = AuthorizeParams(
            response_type="code",
            client_id="finapp-web",
            redirect_uri="http://localhost:5173/auth/callback",
            code_challenge=challenge,
            code_challenge_method="S256",
            state="test-state-123",
        )

        await svc.start_authorization(params)

        redis.setex.assert_called_once()
        call_args = redis.setex.call_args
        key = call_args[0][0]
        assert "pkce" in key
        assert "test-state-123" in key

    async def test_then_returns_frontend_login_url(self):
        from app.core.config import settings

        verifier, challenge = _pkce_pair()
        client_registry = MagicMock()
        client_registry.get_client.return_value = MagicMock(
            redirect_uris=["http://localhost:5173/auth/callback"]
        )
        client_registry.validate_redirect_uri.return_value = True

        redis = AsyncMock()
        redis.setex = AsyncMock()

        svc = _make_service(client_registry=client_registry, redis=redis)

        from app.modules.auth_household.schemas.auth import AuthorizeParams

        params = AuthorizeParams(
            response_type="code",
            client_id="finapp-web",
            redirect_uri="http://localhost:5173/auth/callback",
            code_challenge=challenge,
            code_challenge_method="S256",
            state="my-state",
        )

        url = await svc.start_authorization(params)

        assert settings.frontend_login_url in url or "login" in url
        assert "my-state" in url


class TestGivenInvalidClientIdWhenStartAuthorization:
    async def test_then_raises_error(self):
        """
        Scenario: unregistered client_id
        Given: OIDCClientRegistry.get_client returns None
        When: start_authorization() is called
        Then: an appropriate error is raised (AuthenticationError or ValueError)
        """
        client_registry = MagicMock()
        client_registry.get_client.return_value = None

        svc = _make_service(client_registry=client_registry)

        from app.modules.auth_household.schemas.auth import AuthorizeParams

        params = AuthorizeParams(
            response_type="code",
            client_id="unknown-client",
            redirect_uri="http://anywhere.com/callback",
            code_challenge="abc",
            code_challenge_method="S256",
            state="s",
        )

        with pytest.raises((AuthenticationError, ValueError)):
            await svc.start_authorization(params)


class TestGivenUnregisteredRedirectUriWhenAuthorize:
    async def test_then_raises_error(self):
        client_registry = MagicMock()
        client_registry.get_client.return_value = MagicMock(
            client_id="finapp-web",
            redirect_uris=["http://localhost:5173/auth/callback"],
        )
        client_registry.validate_redirect_uri.return_value = False

        svc = _make_service(client_registry=client_registry)

        from app.modules.auth_household.schemas.auth import AuthorizeParams

        params = AuthorizeParams(
            response_type="code",
            client_id="finapp-web",
            redirect_uri="http://evil.com/steal",
            code_challenge="abc",
            code_challenge_method="S256",
            state="s",
        )

        with pytest.raises((ValueError, AuthenticationError)):
            await svc.start_authorization(params)


# ---------------------------------------------------------------------------
# complete_authorization()
# ---------------------------------------------------------------------------


class TestGivenValidCredentialsWhenCompleteAuthorization:
    async def test_then_creates_authorization_code(self):
        """
        Scenario: user submits login form with correct credentials
        Given: PKCE state found in Redis, credentials valid
        When: complete_authorization() is called
        Then: AuthorizationCodeRepository.create is called once
        """
        verifier, challenge = _pkce_pair()
        user = _make_user()

        redis = AsyncMock()
        # Simulate stored PKCE state
        redis.get.return_value = (
            f'{{"code_challenge":"{challenge}",'
            f'"client_id":"finapp-web",'
            f'"redirect_uri":"http://localhost:5173/auth/callback",'
            f'"scope":"openid email"}}'
        )
        redis.delete = AsyncMock()

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        provider = AsyncMock()
        from app.modules.auth_household.utils.oidc_provider import IdentityClaim

        provider.verify_identity.return_value = IdentityClaim(
            sub=str(user.id),
            email=user.email,
            name=user.full_name,
            email_verified=False,
        )

        code_repo = AsyncMock()
        rate_limiter = AsyncMock()
        rate_limiter.check_locked.return_value = False
        rate_limiter.check_rate.return_value = None  # no rate limit hit

        svc = _make_service(
            user_repo=user_repo,
            code_repo=code_repo,
            provider=provider,
            redis=redis,
            rate_limiter=rate_limiter,
        )

        payload = CompleteAuthSchema(
            email="alice@example.com",
            password="correct",
            state="test-state",
        )

        await svc.complete_authorization(payload)

        code_repo.create.assert_called_once()

    async def test_then_resets_failure_counter(self):
        verifier, challenge = _pkce_pair()
        user = _make_user()

        redis = AsyncMock()
        redis.get.return_value = (
            f'{{"code_challenge":"{challenge}",'
            f'"client_id":"finapp-web",'
            f'"redirect_uri":"http://localhost:5173/auth/callback",'
            f'"scope":"openid"}}'
        )
        redis.delete = AsyncMock()

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        provider = AsyncMock()
        from app.modules.auth_household.utils.oidc_provider import IdentityClaim

        provider.verify_identity.return_value = IdentityClaim(
            sub=str(user.id),
            email=user.email,
            name=user.full_name,
            email_verified=False,
        )

        rate_limiter = AsyncMock()
        rate_limiter.check_locked.return_value = False

        svc = _make_service(
            user_repo=user_repo,
            provider=provider,
            redis=redis,
            rate_limiter=rate_limiter,
        )

        payload = CompleteAuthSchema(email=user.email, password="pw", state="s")
        await svc.complete_authorization(payload)

        rate_limiter.reset_failures.assert_called_once_with(user.id)


class TestGivenWrongPasswordWhenComplete:
    async def test_then_increments_failure_counter(self):
        """
        Scenario: wrong password on login attempt
        Given: user found, credentials invalid
        When: complete_authorization() is called
        Then: rate_limiter.increment_failures is called with the user_id
        """
        verifier, challenge = _pkce_pair()
        user = _make_user()

        redis = AsyncMock()
        redis.get.return_value = (
            f'{{"code_challenge":"{challenge}",'
            f'"client_id":"finapp-web",'
            f'"redirect_uri":"http://localhost:5173/auth/callback",'
            f'"scope":"openid"}}'
        )

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        provider = AsyncMock()
        provider.verify_identity.side_effect = AuthenticationError(
            "Invalid credentials"
        )

        rate_limiter = AsyncMock()
        rate_limiter.check_locked.return_value = False

        svc = _make_service(
            user_repo=user_repo,
            provider=provider,
            redis=redis,
            rate_limiter=rate_limiter,
        )

        payload = CompleteAuthSchema(email=user.email, password="wrong", state="s")

        with pytest.raises(AuthenticationError):
            await svc.complete_authorization(payload)

        rate_limiter.increment_failures.assert_called_once_with(user.id)


class TestGivenTenthFailureWhenComplete:
    async def test_then_sets_lockout_key(self):
        """
        Scenario: 10th consecutive failed login
        Given: rate_limiter reports failure count has hit threshold
        When: complete_authorization() is called
        Then: rate_limiter.lock_account is called
        """
        user = _make_user()

        redis = AsyncMock()
        redis.get.return_value = (
            '{"code_challenge":"x","client_id":"finapp-web",'
            '"redirect_uri":"http://localhost:5173/auth/callback","scope":"openid"}'
        )

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        provider = AsyncMock()
        provider.verify_identity.side_effect = AuthenticationError(
            "Invalid credentials"
        )

        rate_limiter = AsyncMock()
        rate_limiter.check_locked.return_value = False
        rate_limiter.increment_failures.return_value = 10  # threshold reached

        svc = _make_service(
            user_repo=user_repo,
            provider=provider,
            redis=redis,
            rate_limiter=rate_limiter,
        )

        with pytest.raises(AuthenticationError):
            await svc.complete_authorization(
                CompleteAuthSchema(email=user.email, password="bad", state="s")
            )

        rate_limiter.lock_account.assert_called_once_with(user.id)


# ---------------------------------------------------------------------------
# exchange_code()
# ---------------------------------------------------------------------------


class TestGivenValidCodeAndVerifierWhenExchange:
    async def test_then_returns_token_response(self):
        """
        Scenario: successful authorization code exchange
        Given: code in DB, verifier matches challenge
        When: exchange_code() is called
        Then: a TokenResponse with access_token and id_token is returned
        """
        verifier, challenge = _pkce_pair()
        user = _make_user()
        hh_id = uuid.uuid4()
        membership = _make_membership(user.id, hh_id)

        code_record = MagicMock()
        code_record.code_challenge = challenge
        code_record.code_challenge_method = "S256"
        code_record.client_id = "finapp-web"
        code_record.redirect_uri = "http://localhost:5173/auth/callback"
        code_record.user_id = user.id
        code_record.expires_at = datetime.now(UTC) + timedelta(seconds=60)
        code_record.used_at = None

        code_repo = AsyncMock()
        code_repo.get_by_code.return_value = code_record

        user_repo = AsyncMock()
        user_repo.get_with_memberships.return_value = (user, [membership])

        rt_repo = AsyncMock()

        token_service = MagicMock()
        token_service.create_access_token.return_value = "access.token.here"
        token_service.create_id_token.return_value = "id.token.here"
        token_service.generate_refresh_token.return_value = secrets.token_urlsafe(64)
        token_service.hash_token.return_value = "deadbeef" * 8

        svc = _make_service(
            code_repo=code_repo,
            user_repo=user_repo,
            rt_repo=rt_repo,
            token_service=token_service,
        )

        params = TokenRequestParams(
            grant_type="authorization_code",
            code="rawcode",
            code_verifier=verifier,
            client_id="finapp-web",
            redirect_uri="http://localhost:5173/auth/callback",
        )

        result = await svc.exchange_code(params)

        assert result.access_token == "access.token.here"
        assert result.id_token == "id.token.here"
        assert result.token_type == "Bearer"


class TestGivenWrongVerifierWhenExchange:
    async def test_then_raises_invalid_grant(self):
        """
        Scenario: PKCE verifier does not match stored challenge
        Given: authorization code in DB with challenge for a DIFFERENT verifier
        When: exchange_code() is called with wrong code_verifier
        Then: an error with code 'invalid_grant' or AuthenticationError is raised
        """
        _, challenge = _pkce_pair()
        wrong_verifier = secrets.token_urlsafe(64)  # unrelated verifier

        code_record = MagicMock()
        code_record.code_challenge = challenge
        code_record.code_challenge_method = "S256"
        code_record.client_id = "finapp-web"
        code_record.redirect_uri = "http://localhost:5173/auth/callback"
        code_record.user_id = uuid.uuid4()
        code_record.expires_at = datetime.now(UTC) + timedelta(seconds=60)
        code_record.used_at = None

        code_repo = AsyncMock()
        code_repo.get_by_code.return_value = code_record

        svc = _make_service(code_repo=code_repo)

        params = TokenRequestParams(
            grant_type="authorization_code",
            code="rawcode",
            code_verifier=wrong_verifier,
            client_id="finapp-web",
            redirect_uri="http://localhost:5173/auth/callback",
        )

        with pytest.raises((AuthenticationError, ValueError)):
            await svc.exchange_code(params)


class TestGivenUsedCodeWhenExchange:
    async def test_then_raises_error(self):
        """
        Scenario: authorization code used a second time
        Given: code_repo.get_by_code returns None (deleted on first use)
        When: exchange_code() is called
        Then: an error is raised (code not found)
        """
        code_repo = AsyncMock()
        code_repo.get_by_code.return_value = None  # deleted after first use

        svc = _make_service(code_repo=code_repo)

        params = TokenRequestParams(
            grant_type="authorization_code",
            code="already-used",
            code_verifier="anything",
            client_id="finapp-web",
            redirect_uri="http://localhost:5173/auth/callback",
        )

        with pytest.raises((AuthenticationError, ValueError)):
            await svc.exchange_code(params)


# ---------------------------------------------------------------------------
# refresh_tokens()
# ---------------------------------------------------------------------------


class TestGivenValidRefreshTokenWhenRefresh:
    async def test_then_rotates_token(self):
        """
        Scenario: silent token refresh
        Given: valid, unconsumed refresh token
        When: refresh_tokens() is called
        Then: old token is marked consumed and a new token row is inserted
        """
        raw_token = secrets.token_urlsafe(64)
        user = _make_user()
        hh_id = uuid.uuid4()
        membership = _make_membership(user.id, hh_id)

        token_record = MagicMock()
        token_record.user_id = user.id
        token_record.family_id = uuid.uuid4()
        token_record.is_revoked = False
        token_record.is_family_revoked = False
        token_record.expires_at = datetime.now(UTC) + timedelta(days=7)

        rt_repo = AsyncMock()
        rt_repo.get_by_hash.return_value = token_record
        rt_repo.revoke = AsyncMock()
        rt_repo.create.return_value = MagicMock()

        user_repo = AsyncMock()
        user_repo.get_with_memberships.return_value = (user, [membership])

        token_service = MagicMock()
        token_service.create_access_token.return_value = "new.access.token"
        token_service.create_id_token.return_value = "new.id.token"
        token_service.generate_refresh_token.return_value = secrets.token_urlsafe(64)
        token_service.hash_token.return_value = "abc123"

        svc = _make_service(
            rt_repo=rt_repo, user_repo=user_repo, token_service=token_service
        )

        result = await svc.refresh_tokens(raw_token)

        rt_repo.revoke.assert_called_once()
        rt_repo.create.assert_called_once()
        assert result.access_token == "new.access.token"


class TestGivenConsumedRefreshTokenWhenRefresh:
    async def test_then_revokes_entire_family(self):
        """
        Scenario: refresh token reuse detected (token theft)
        Given: token record is already revoked (is_revoked=True)
        When: refresh_tokens() is called with that token
        Then: the entire token family is revoked and AuthenticationError is raised
        """
        raw_token = secrets.token_urlsafe(64)
        family_id = uuid.uuid4()

        token_record = MagicMock()
        token_record.user_id = uuid.uuid4()
        token_record.family_id = family_id
        token_record.is_revoked = True  # already consumed
        token_record.is_family_revoked = False
        token_record.expires_at = datetime.now(UTC) + timedelta(days=7)

        rt_repo = AsyncMock()
        rt_repo.get_by_hash.return_value = token_record

        svc = _make_service(rt_repo=rt_repo)

        with pytest.raises(AuthenticationError):
            await svc.refresh_tokens(raw_token)

        rt_repo.revoke_family.assert_called_once_with(family_id)
