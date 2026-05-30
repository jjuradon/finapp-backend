"""
Integration tests for POST /v1/auth/register.

Scenario: new user + household creation.
"""

from httpx import AsyncClient

_VALID_PAYLOAD = {
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User",
    "household_name": "New Household",
}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGivenValidPayloadWhenPostRegister:
    async def test_then_returns_201(self, async_client: AsyncClient):
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        assert resp.status_code == 201

    async def test_then_response_has_envelope(self, async_client: AsyncClient):
        """
        Scenario: successful registration
        Given: valid payload
        When: POST /v1/auth/register
        Then: response body has data, meta, error keys in the standard envelope
        """
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        body = resp.json()

        assert "data" in body
        assert "meta" in body
        assert "error" in body
        assert body["error"] is None

    async def test_then_meta_has_request_id_and_timestamp(
        self, async_client: AsyncClient
    ):
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        meta = resp.json()["meta"]
        assert "request_id" in meta
        assert "timestamp" in meta

    async def test_then_data_has_required_fields(self, async_client: AsyncClient):
        """data field must contain user_id, email, full_name, household_id, role."""
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        data = resp.json()["data"]

        assert "user_id" in data
        assert "email" in data
        assert "full_name" in data
        assert "household_id" in data
        assert "role" in data

    async def test_then_role_is_owner(self, async_client: AsyncClient):
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        assert resp.json()["data"]["role"] == "owner"

    async def test_then_returned_email_matches_input(self, async_client: AsyncClient):
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        assert resp.json()["data"]["email"] == _VALID_PAYLOAD["email"]


# ---------------------------------------------------------------------------
# Duplicate email
# ---------------------------------------------------------------------------


class TestGivenDuplicateEmailWhenPostRegister:
    async def test_then_returns_409(self, async_client: AsyncClient):
        """
        Scenario: email already registered
        Given: first registration succeeds
        When: second registration with same email
        Then: 409 Conflict
        """
        await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        assert resp.status_code == 409

    async def test_then_response_has_error_code(self, async_client: AsyncClient):
        await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        resp = await async_client.post("/v1/auth/register", json=_VALID_PAYLOAD)
        body = resp.json()
        assert body["data"] is None
        assert body["error"] is not None
        assert "code" in body["error"]


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestGivenMissingFieldWhenPostRegister:
    async def test_then_returns_400(self, async_client: AsyncClient):
        """Required field omitted → 400."""
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "full_name"}
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 400

    async def test_then_response_has_envelope_with_error(
        self, async_client: AsyncClient
    ):
        payload = {"email": "a@b.com"}  # missing password, full_name, household_name
        resp = await async_client.post("/v1/auth/register", json=payload)
        body = resp.json()
        assert body["data"] is None
        assert body["error"] is not None


class TestGivenShortPasswordWhenPostRegister:
    async def test_then_returns_400(self, async_client: AsyncClient):
        """Password must be at least 8 characters."""
        payload = {**_VALID_PAYLOAD, "password": "short"}
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 400


class TestGivenInvalidEmailWhenPostRegister:
    async def test_then_returns_400(self, async_client: AsyncClient):
        payload = {**_VALID_PAYLOAD, "email": "not-an-email"}
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 400


class TestGivenPasswordTooLongWhenPostRegister:
    async def test_then_returns_400(self, async_client: AsyncClient):
        """Password max length is 128 characters."""
        payload = {**_VALID_PAYLOAD, "password": "x" * 129}
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 400


class TestGivenExtraUnknownFieldWhenPostRegister:
    async def test_then_returns_400(self, async_client: AsyncClient):
        """extra='forbid' must reject unknown fields."""
        payload = {**_VALID_PAYLOAD, "unexpected_field": "value"}
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code in (400, 422)
