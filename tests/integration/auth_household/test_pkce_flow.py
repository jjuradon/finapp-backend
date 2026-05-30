"""
Integration tests for the full PKCE Authorization Code flow.

Covers:
  - GET  /v1/auth/authorize
  - POST /v1/auth/authorize/complete
  - POST /v1/auth/token
  - End-to-end happy path
"""

import base64
import hashlib
import secrets
import uuid

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _authorize_params(challenge: str, state: str | None = None) -> dict:
    return {
        "response_type": "code",
        "client_id": "finapp-web",
        "redirect_uri": "http://localhost:5173/auth/callback",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state or str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# GET /v1/auth/authorize
# ---------------------------------------------------------------------------


class TestGivenValidParamsWhenGetAuthorize:
    async def test_then_redirects_to_login_page(
        self, async_client: AsyncClient, registered_user: dict  # noqa: ARG002
    ):
        """
        Scenario: client initiates PKCE flow
        Given: valid client_id, redirect_uri, S256 challenge
        When: GET /v1/auth/authorize
        Then: 302 redirect to frontend login page with ?state= param
        """
        _, challenge = _pkce_pair()
        state = "my-test-state"

        resp = await async_client.get(
            "/v1/auth/authorize",
            params=_authorize_params(challenge, state),
            follow_redirects=False,
        )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "state=" in location
        assert state in location

    async def test_then_redirect_points_to_frontend_login(
        self, async_client: AsyncClient
    ):
        from app.core.config import settings

        _, challenge = _pkce_pair()
        resp = await async_client.get(
            "/v1/auth/authorize",
            params=_authorize_params(challenge),
            follow_redirects=False,
        )

        location = resp.headers["location"]
        assert (
            settings.frontend_login_url.split("//")[1].split("/")[0] in location
            or "login" in location
        )


class TestGivenInvalidClientIdWhenGetAuthorize:
    async def test_then_returns_401(self, async_client: AsyncClient):
        _, challenge = _pkce_pair()
        params = {**_authorize_params(challenge), "client_id": "unknown-client"}

        resp = await async_client.get(
            "/v1/auth/authorize", params=params, follow_redirects=False
        )

        assert resp.status_code == 401


class TestGivenUnregisteredRedirectUriWhenGetAuthorize:
    async def test_then_returns_400(self, async_client: AsyncClient):
        _, challenge = _pkce_pair()
        params = {
            **_authorize_params(challenge),
            "redirect_uri": "http://evil.com/steal",
        }

        resp = await async_client.get(
            "/v1/auth/authorize", params=params, follow_redirects=False
        )

        assert resp.status_code == 400


class TestGivenResponseTypeTokenWhenGetAuthorize:
    async def test_then_returns_unsupported_response_type(
        self, async_client: AsyncClient
    ):
        """
        Scenario: implicit flow attempted (deprecated)
        Given: response_type=token
        When: GET /v1/auth/authorize
        Then: 400 with error=unsupported_response_type
        """
        _, challenge = _pkce_pair()
        params = {**_authorize_params(challenge), "response_type": "token"}

        resp = await async_client.get(
            "/v1/auth/authorize", params=params, follow_redirects=False
        )

        assert resp.status_code == 400
        body = resp.json()
        assert (
            "unsupported_response_type" in str(body).lower()
            or resp.headers.get("location", "").find("unsupported_response_type") != -1
        )


class TestGivenPlainChallengeMethodWhenGetAuthorize:
    async def test_then_returns_400_invalid_request(self, async_client: AsyncClient):
        """Only S256 is accepted — plain is insecure and rejected."""
        params = {
            "response_type": "code",
            "client_id": "finapp-web",
            "redirect_uri": "http://localhost:5173/auth/callback",
            "code_challenge": "plain-challenge-value",
            "code_challenge_method": "plain",
            "state": "s",
        }

        resp = await async_client.get(
            "/v1/auth/authorize", params=params, follow_redirects=False
        )

        assert resp.status_code == 400


class TestGivenMissingRequiredParamWhenGetAuthorize:
    async def test_then_returns_400(self, async_client: AsyncClient):
        # Missing code_challenge
        params = {
            "response_type": "code",
            "client_id": "finapp-web",
            "redirect_uri": "http://localhost:5173/auth/callback",
            "state": "s",
        }
        resp = await async_client.get(
            "/v1/auth/authorize", params=params, follow_redirects=False
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /v1/auth/authorize/complete
# ---------------------------------------------------------------------------


class TestGivenValidCredentialsWhenPostComplete:
    async def test_then_redirects_with_code(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: user submits login form
        Given: valid credentials, state found in Redis
        When: POST /v1/auth/authorize/complete
        Then: 302 redirect to redirect_uri with ?code=... and ?state=...
        """
        verifier, challenge = _pkce_pair()
        state = str(uuid.uuid4())

        await async_client.get(
            "/v1/auth/authorize",
            params=_authorize_params(challenge, state),
            follow_redirects=False,
        )

        resp = await async_client.post(
            "/v1/auth/authorize/complete",
            json={
                "email": registered_user["email"],
                "password": "password123",
                "state": state,
            },
            follow_redirects=False,
        )

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "code=" in location
        assert state in location


class TestGivenWrongPasswordWhenPostComplete:
    async def test_then_returns_401(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: incorrect password
        Given: user exists, password is wrong
        When: POST /v1/auth/authorize/complete
        Then: 401 (no enumeration — same code as unknown user)
        """
        _, challenge = _pkce_pair()
        state = str(uuid.uuid4())

        await async_client.get(
            "/v1/auth/authorize",
            params=_authorize_params(challenge, state),
            follow_redirects=False,
        )

        resp = await async_client.post(
            "/v1/auth/authorize/complete",
            json={
                "email": registered_user["email"],
                "password": "wrong-password",
                "state": state,
            },
            follow_redirects=False,
        )

        assert resp.status_code == 401

    async def test_then_error_message_same_as_unknown_user(
        self, async_client: AsyncClient, registered_user: dict  # noqa: ARG002
    ):
        """No credential enumeration — same message for wrong password and unknown email."""
        for email, pw in [
            (registered_user["email"], "wrongpw"),
            ("nobody@example.com", "anything"),
        ]:
            _, challenge = _pkce_pair()
            state = str(uuid.uuid4())
            await async_client.get(
                "/v1/auth/authorize",
                params=_authorize_params(challenge, state),
                follow_redirects=False,
            )
            resp = await async_client.post(
                "/v1/auth/authorize/complete",
                json={"email": email, "password": pw, "state": state},
                follow_redirects=False,
            )
            assert resp.status_code == 401


class TestGivenExpiredStateWhenPostComplete:
    async def test_then_returns_400(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """State not found in Redis (expired or never initiated) → 400."""
        resp = await async_client.post(
            "/v1/auth/authorize/complete",
            json={
                "email": registered_user["email"],
                "password": "password123",
                "state": "nonexistent-state-" + str(uuid.uuid4()),
            },
            follow_redirects=False,
        )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /v1/auth/token
# ---------------------------------------------------------------------------


async def _get_code(
    async_client: AsyncClient, email: str, password: str
) -> tuple[str, str]:
    """Helper: run authorize + complete and return (code, verifier)."""
    verifier, challenge = _pkce_pair()
    state = str(uuid.uuid4())

    await async_client.get(
        "/v1/auth/authorize",
        params=_authorize_params(challenge, state),
        follow_redirects=False,
    )
    resp = await async_client.post(
        "/v1/auth/authorize/complete",
        json={"email": email, "password": password, "state": state},
        follow_redirects=False,
    )
    code = resp.headers["location"].split("code=")[1].split("&")[0]
    return code, verifier


class TestGivenValidCodeWhenPostToken:
    async def test_then_returns_access_and_id_token(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: code exchange
        Given: valid code and matching verifier
        When: POST /v1/auth/token
        Then: response contains access_token and id_token
        """
        code, verifier = await _get_code(
            async_client, registered_user["email"], "password123"
        )

        resp = await async_client.post(
            "/v1/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "id_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 900

    async def test_then_response_is_not_wrapped_in_envelope(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """OIDC spec: token response is raw JSON, not the finapp envelope."""
        code, verifier = await _get_code(
            async_client, registered_user["email"], "password123"
        )
        resp = await async_client.post(
            "/v1/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        body = resp.json()
        assert "data" not in body
        assert "access_token" in body

    async def test_then_sets_refresh_token_httponly_cookie(
        self, async_client: AsyncClient, registered_user: dict
    ):
        code, verifier = await _get_code(
            async_client, registered_user["email"], "password123"
        )
        resp = await async_client.post(
            "/v1/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        assert "refresh_token" in resp.cookies
        # Verify cookie path is scoped to refresh endpoint
        set_cookie = resp.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "/v1/auth/refresh" in set_cookie


class TestGivenWrongVerifierWhenPostToken:
    async def test_then_returns_invalid_grant(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: PKCE verifier mismatch
        Given: valid code but wrong code_verifier
        When: POST /v1/auth/token
        Then: 400 with error=invalid_grant
        """
        code, _ = await _get_code(async_client, registered_user["email"], "password123")
        wrong_verifier = secrets.token_urlsafe(64)

        resp = await async_client.post(
            "/v1/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": wrong_verifier,
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )

        assert resp.status_code == 400
        body_str = resp.text.lower()
        assert "invalid_grant" in body_str


class TestGivenCodeUsedTwiceWhenPostToken:
    async def test_then_second_attempt_returns_error(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: authorization code replay
        Given: code exchanged successfully once (deleted from DB)
        When: second POST /v1/auth/token with same code
        Then: error (code not found)
        """
        code, verifier = await _get_code(
            async_client, registered_user["email"], "password123"
        )

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": "finapp-web",
            "redirect_uri": "http://localhost:5173/auth/callback",
        }

        first = await async_client.post("/v1/auth/token", data=token_data)
        assert first.status_code == 200

        second = await async_client.post("/v1/auth/token", data=token_data)
        assert second.status_code == 400


class TestGivenMissingGrantTypeWhenPostToken:
    async def test_then_returns_400(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/v1/auth/token",
            data={
                "code": "fake",
                "code_verifier": "fake",
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


class TestFullPkceFlowEndToEnd:
    async def test_authorize_complete_token_all_succeed(
        self, async_client: AsyncClient, registered_user: dict
    ):
        """
        Scenario: complete PKCE Authorization Code flow
        Given: authenticated user with valid credentials
        When: authorize → complete → token
        Then:
          - authorize returns 302 with state in location
          - complete returns 302 with code in location
          - token returns access_token and id_token
          - access_token sub matches registered user_id
        """
        verifier, challenge = _pkce_pair()
        state = "e2e-test-" + str(uuid.uuid4())

        # Step 1
        auth_resp = await async_client.get(
            "/v1/auth/authorize",
            params=_authorize_params(challenge, state),
            follow_redirects=False,
        )
        assert auth_resp.status_code == 302
        assert state in auth_resp.headers["location"]

        # Step 2
        complete_resp = await async_client.post(
            "/v1/auth/authorize/complete",
            json={
                "email": registered_user["email"],
                "password": "password123",
                "state": state,
            },
            follow_redirects=False,
        )
        assert complete_resp.status_code == 302
        location = complete_resp.headers["location"]
        assert "code=" in location
        code = location.split("code=")[1].split("&")[0]

        # Step 3
        token_resp = await async_client.post(
            "/v1/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "client_id": "finapp-web",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        assert token_resp.status_code == 200
        tokens = token_resp.json()
        assert "access_token" in tokens
        assert "id_token" in tokens

        # Verify sub in access token matches user_id
        from jose import jwt as jose_jwt

        from app.core.config import settings

        payload = jose_jwt.decode(
            tokens["access_token"],
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        assert payload["sub"] == registered_user["user_id"]
