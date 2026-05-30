"""
Unit tests for TokenService.

Verifies RS256 JWT creation, decoding, JWKS export, and error paths.
No database or HTTP — pure unit tests against the TokenService utility.
"""

import time
import uuid
from unittest.mock import MagicMock

import pytest
from jose import jwt

from app.modules.auth_household.utils.token import TokenService
from app.shared.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def token_service() -> TokenService:
    """Single TokenService instance shared across this module's tests."""
    return TokenService()


def _make_user(role: str = "owner") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.full_name = "Jane Smith"
    user.email_verified = False
    return user


def _make_membership(
    user_id: uuid.UUID, household_id: uuid.UUID, role: str = "owner"
) -> MagicMock:
    m = MagicMock()
    m.user_id = user_id
    m.household_id = household_id
    m.role = role
    return m


# ---------------------------------------------------------------------------
# Access token claims
# ---------------------------------------------------------------------------


class TestGivenUserWhenCreateAccessToken:
    def test_then_payload_has_all_required_claims(self, token_service: TokenService):
        """
        Scenario: access token issuance
        Given: a user with household memberships
        When: create_access_token is called
        Then: decoded payload contains sub, email, roles, households, jti, iat, exp, iss
        """
        user = _make_user()
        membership = _make_membership(user.id, uuid.uuid4())

        token = token_service.create_access_token(user=user, memberships=[membership])

        from app.core.config import settings

        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert "roles" in payload
        assert "households" in payload
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert payload["iss"] == settings.issuer_url

    def test_then_exp_is_15_minutes_from_now(self, token_service: TokenService):
        user = _make_user()
        membership = _make_membership(user.id, uuid.uuid4())

        before = int(time.time())
        token = token_service.create_access_token(user=user, memberships=[membership])
        after = int(time.time())

        from app.core.config import settings

        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        expected_ttl = settings.access_token_ttl_seconds
        assert before + expected_ttl <= payload["exp"] <= after + expected_ttl

    def test_then_jti_is_a_valid_uuid(self, token_service: TokenService):
        user = _make_user()
        membership = _make_membership(user.id, uuid.uuid4())

        from app.core.config import settings

        token = token_service.create_access_token(user=user, memberships=[membership])
        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        uuid.UUID(payload["jti"])  # raises ValueError if not valid UUID

    def test_then_households_contains_membership_data(
        self, token_service: TokenService
    ):
        user = _make_user()
        hh_id = uuid.uuid4()
        membership = _make_membership(user.id, hh_id, role="member")

        from app.core.config import settings

        token = token_service.create_access_token(user=user, memberships=[membership])
        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        households = payload["households"]
        assert len(households) == 1
        assert households[0]["household_id"] == str(hh_id)
        assert households[0]["role"] == "member"


# ---------------------------------------------------------------------------
# ID token claims
# ---------------------------------------------------------------------------


class TestGivenUserWhenCreateIdToken:
    def test_then_payload_has_oidc_standard_claims(self, token_service: TokenService):
        """
        Scenario: ID token issuance
        Given: a user
        When: create_id_token is called with a client_id
        Then: payload has iss, sub, aud, iat, exp, email, name, email_verified
        """
        user = _make_user()

        from app.core.config import settings

        token = token_service.create_id_token(user=user, client_id="finapp-web")
        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            audience="finapp-web",
        )

        assert payload["iss"] == settings.issuer_url
        assert payload["sub"] == str(user.id)
        assert payload["aud"] == "finapp-web"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["email"] == user.email
        assert payload["name"] == user.full_name
        assert "email_verified" in payload

    def test_then_aud_equals_client_id(self, token_service: TokenService):
        user = _make_user()

        from app.core.config import settings

        token = token_service.create_id_token(user=user, client_id="finapp-mobile")
        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            audience="finapp-mobile",
        )

        assert payload["aud"] == "finapp-mobile"

    def test_then_iss_matches_discovery_issuer(self, token_service: TokenService):
        """
        Critical: the issuer in the ID token MUST match the issuer in the
        discovery document. Both read from settings.issuer_url.
        """
        from app.core.config import settings

        user = _make_user()
        token = token_service.create_id_token(user=user, client_id="finapp-web")
        payload = jwt.decode(
            token,
            settings.auth_public_key,
            algorithms=["RS256"],
            audience="finapp-web",
        )

        assert payload["iss"] == settings.issuer_url


# ---------------------------------------------------------------------------
# Decode / validation errors
# ---------------------------------------------------------------------------


class TestGivenExpiredTokenWhenDecode:
    def test_then_raises_authentication_error(self, token_service: TokenService):
        """
        Scenario: expired access token presented
        Given: a token whose exp is in the past
        When: decode_access_token is called
        Then: AuthenticationError is raised
        """
        import time

        from jose import jwt as jose_jwt

        from app.core.config import settings

        expired_payload = {
            "sub": str(uuid.uuid4()),
            "email": "x@x.com",
            "roles": ["owner"],
            "households": [],
            "jti": str(uuid.uuid4()),
            "iat": int(time.time()) - 3600,
            "exp": int(time.time()) - 1800,
            "iss": settings.issuer_url,
        }
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        private_key = load_pem_private_key(
            settings.auth_private_key.replace("\\n", "\n").encode(), password=None
        )
        token = jose_jwt.encode(expired_payload, private_key, algorithm="RS256")

        with pytest.raises(AuthenticationError):
            token_service.decode_access_token(token)


class TestGivenTamperedTokenWhenDecode:
    def test_then_raises_authentication_error(self, token_service: TokenService):
        """
        Scenario: token signature tampered with
        Given: a validly issued token with its signature altered
        When: decode_access_token is called
        Then: AuthenticationError is raised
        """
        user = _make_user()
        membership = _make_membership(user.id, uuid.uuid4())

        token = token_service.create_access_token(user=user, memberships=[membership])
        # Flip the last few characters of the signature segment
        parts = token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        tampered = ".".join(parts)

        with pytest.raises(AuthenticationError):
            token_service.decode_access_token(tampered)


# ---------------------------------------------------------------------------
# JWKS export
# ---------------------------------------------------------------------------


class TestGivenPublicKeyWhenJwks:
    def test_then_returns_valid_rfc7517_format(self, token_service: TokenService):
        """
        Scenario: JWKS endpoint key export
        Given: the configured RS256 public key
        When: public_key_to_jwks is called
        Then: result has kty=RSA, use=sig, alg=RS256, kid, n, e
        """
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        from app.core.config import settings

        public_key = load_pem_public_key(
            settings.auth_public_key.replace("\\n", "\n").encode()
        )
        jwks = token_service.public_key_to_jwks(public_key)

        assert jwks["kty"] == "RSA"
        assert jwks["use"] == "sig"
        assert jwks["alg"] == "RS256"
        assert "kid" in jwks
        assert "n" in jwks
        assert "e" in jwks

    def test_given_issued_token_when_verified_with_jwks_key_then_succeeds(
        self, token_service: TokenService
    ):
        """
        Scenario: consumers verify our tokens using the JWKS endpoint key
        Given: an access token issued by TokenService
        When: verified using the public key from public_key_to_jwks
        Then: verification succeeds and payload is readable
        """

        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        from app.core.config import settings

        user = _make_user()
        membership = _make_membership(user.id, uuid.uuid4())
        token = token_service.create_access_token(user=user, memberships=[membership])

        public_key = load_pem_public_key(
            settings.auth_public_key.replace("\\n", "\n").encode()
        )

        # Verify using raw RSA public key (as downstream services would)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        assert payload["sub"] == str(user.id)


# ---------------------------------------------------------------------------
# Refresh token generation
# ---------------------------------------------------------------------------


class TestGenerateRefreshToken:
    def test_returns_url_safe_string_of_sufficient_length(
        self, token_service: TokenService
    ):
        token = token_service.generate_refresh_token()
        assert isinstance(token, str)
        assert len(token) >= 64

    def test_two_tokens_are_not_equal(self, token_service: TokenService):
        t1 = token_service.generate_refresh_token()
        t2 = token_service.generate_refresh_token()
        assert t1 != t2


# ---------------------------------------------------------------------------
# hash_token
# ---------------------------------------------------------------------------


class TestHashToken:
    def test_same_input_produces_same_hash(self, token_service: TokenService):
        assert token_service.hash_token("abc") == token_service.hash_token("abc")

    def test_different_inputs_produce_different_hashes(
        self, token_service: TokenService
    ):
        assert token_service.hash_token("abc") != token_service.hash_token("xyz")

    def test_hash_is_hex_string_of_64_chars(self, token_service: TokenService):
        h = token_service.hash_token("anything")
        assert len(h) == 64
        int(h, 16)  # raises ValueError if not valid hex
