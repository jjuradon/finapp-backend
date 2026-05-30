"""
Integration tests for POST /v1/auth/refresh.

Scenario: silent token refresh via HttpOnly refresh_token cookie.
Covers: rotation, reuse detection (family revocation), missing cookie.
"""

from httpx import AsyncClient


class TestGivenValidRefreshCookieWhenPostRefresh:
    async def test_then_returns_200(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        """
        Scenario: successful silent refresh
        Given: valid refresh_token cookie
        When: POST /v1/auth/refresh
        Then: 200 with new tokens
        """
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": auth_token_with_cookie["refresh_token_cookie"]},
        )
        assert resp.status_code == 200

    async def test_then_new_tokens_include_access_and_id_token(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        """
        Scenario: refresh response shape
        Given: valid cookie
        When: POST /v1/auth/refresh
        Then: both access_token and id_token are in the response
        """
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": auth_token_with_cookie["refresh_token_cookie"]},
        )
        body = resp.json()
        assert "access_token" in body
        assert "id_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 900

    async def test_then_response_is_not_wrapped_in_envelope(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": auth_token_with_cookie["refresh_token_cookie"]},
        )
        body = resp.json()
        assert "data" not in body
        assert "access_token" in body

    async def test_then_sets_new_refresh_token_cookie(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": auth_token_with_cookie["refresh_token_cookie"]},
        )
        assert "refresh_token" in resp.cookies
        new_cookie = resp.cookies["refresh_token"]
        assert new_cookie != auth_token_with_cookie["refresh_token_cookie"]

    async def test_then_new_refresh_cookie_is_httponly(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": auth_token_with_cookie["refresh_token_cookie"]},
        )
        set_cookie = resp.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie


class TestGivenOldTokenAfterRotationWhenPostRefresh:
    async def test_then_returns_401(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        """
        Scenario: refresh token rotation
        Given: original refresh cookie used once (token is now consumed)
        When: POST /v1/auth/refresh with the original (old) cookie
        Then: 401 — token has been rotated out
        """
        original_cookie = auth_token_with_cookie["refresh_token_cookie"]

        # First refresh — consumes original, issues new
        first = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": original_cookie},
        )
        assert first.status_code == 200

        # Second refresh with old cookie — must fail
        second = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": original_cookie},
        )
        assert second.status_code == 401


class TestGivenReusedTokenWhenPostRefresh:
    async def test_then_revokes_entire_family(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        """
        Scenario: refresh token reuse (theft detection)
        Given: original token used to get a new token (token A → token B)
        When: original token (A) used again
        Then: 401 AND token B is also invalidated (family revoked)
        """
        original_cookie = auth_token_with_cookie["refresh_token_cookie"]

        # Legitimate rotation: A → B
        rotate = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": original_cookie},
        )
        assert rotate.status_code == 200
        new_cookie = rotate.cookies["refresh_token"]

        # Attacker replays original token A — reuse detected
        reuse = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": original_cookie},
        )
        assert reuse.status_code == 401

        # Token B (legitimate holder's next token) must also be invalidated
        after_revoke = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": new_cookie},
        )
        assert after_revoke.status_code == 401


class TestGivenNoCookieWhenPostRefresh:
    async def test_then_returns_401(self, async_client: AsyncClient):
        """
        Scenario: no refresh cookie presented
        Given: request with no cookie
        When: POST /v1/auth/refresh
        Then: 401
        """
        resp = await async_client.post("/v1/auth/refresh")
        assert resp.status_code == 401


class TestGivenExpiredRefreshTokenWhenPostRefresh:
    async def test_then_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/v1/auth/refresh",
            cookies={"refresh_token": "expired-or-invalid-token"},
        )
        assert resp.status_code == 401
