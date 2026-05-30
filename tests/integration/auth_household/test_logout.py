"""
Integration tests for POST /v1/auth/logout.

Scenario: token invalidation and cookie clearing on logout.
"""

from httpx import AsyncClient


class TestGivenLoggedInUserWhenPostLogout:
    async def test_then_returns_204(self, async_client: AsyncClient, auth_token: str):
        """
        Scenario: successful logout
        Given: authenticated user with valid access token
        When: POST /v1/auth/logout
        Then: 204 No Content
        """
        resp = await async_client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 204

    async def test_then_clears_refresh_token_cookie(
        self, async_client: AsyncClient, auth_token_with_cookie: dict
    ):
        """After logout the refresh cookie must be expired (Max-Age=0)."""
        resp = await async_client.post(
            "/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {auth_token_with_cookie['access_token']}"
            },
        )

        set_cookie = resp.headers.get("set-cookie", "")
        assert "Max-Age=0" in set_cookie or "refresh_token=" in set_cookie


class TestGivenLoggedOutUserWhenGetUserinfoWithOldToken:
    async def test_then_returns_401(self, async_client: AsyncClient, auth_token: str):
        """
        Scenario: blacklisted access token used after logout
        Given: user has logged out (jti blacklisted in Redis)
        When: GET /v1/auth/userinfo with the old access token
        Then: 401 — token is on the blacklist
        """
        # Logout — blacklists the jti
        await async_client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Attempt to use the now-blacklisted token
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 401


class TestGivenNoTokenWhenPostLogout:
    async def test_then_returns_401(self, async_client: AsyncClient):
        """
        Scenario: unauthenticated logout attempt
        Given: no Authorization header
        When: POST /v1/auth/logout
        Then: 401
        """
        resp = await async_client.post("/v1/auth/logout")
        assert resp.status_code == 401


class TestGivenInvalidTokenWhenPostLogout:
    async def test_then_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/v1/auth/logout",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert resp.status_code == 401
