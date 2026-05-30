"""
Integration tests for GET /v1/auth/userinfo.

Scenario: authenticated user fetching their own OIDC claims.
"""

from httpx import AsyncClient


class TestGivenValidTokenWhenGetUserinfo:
    async def test_then_returns_200(self, async_client: AsyncClient, auth_token: str):
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200

    async def test_then_response_is_not_wrapped_in_envelope(
        self, async_client: AsyncClient, auth_token: str
    ):
        """OIDC spec: userinfo is raw JSON, not the finapp envelope."""
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        body = resp.json()
        assert "data" not in body
        assert "sub" in body

    async def test_then_returns_oidc_standard_claims(
        self, async_client: AsyncClient, auth_token: str
    ):
        """
        Scenario: OIDC userinfo standard claims
        Given: authenticated user
        When: GET /v1/auth/userinfo
        Then: sub, email, name, email_verified are all present
        """
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        body = resp.json()

        assert "sub" in body
        assert "email" in body
        assert "name" in body
        assert "email_verified" in body

    async def test_then_returns_custom_finapp_claims(
        self, async_client: AsyncClient, auth_token: str
    ):
        """
        Scenario: finapp-specific claims
        Given: authenticated user with household membership
        When: GET /v1/auth/userinfo
        Then: roles and households are present
        """
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        body = resp.json()

        assert "roles" in body
        assert "households" in body
        assert isinstance(body["roles"], list)
        assert isinstance(body["households"], list)

    async def test_then_households_contains_household_id_and_role(
        self, async_client: AsyncClient, auth_token: str
    ):
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        household = resp.json()["households"][0]

        assert "household_id" in household
        assert "role" in household

    async def test_then_sub_is_a_uuid(self, async_client: AsyncClient, auth_token: str):
        import uuid

        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        uuid.UUID(resp.json()["sub"])  # raises if not a valid UUID


class TestGivenNoTokenWhenGetUserinfo:
    async def test_then_returns_401(self, async_client: AsyncClient):
        """
        Scenario: unauthenticated request
        Given: no Authorization header
        When: GET /v1/auth/userinfo
        Then: 401
        """
        resp = await async_client.get("/v1/auth/userinfo")
        assert resp.status_code == 401


class TestGivenInvalidTokenWhenGetUserinfo:
    async def test_then_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert resp.status_code == 401

    async def test_given_malformed_bearer_then_returns_401(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get(
            "/v1/auth/userinfo",
            headers={"Authorization": "NotBearer sometoken"},
        )
        assert resp.status_code == 401
