"""
Integration tests for OIDC Discovery and JWKS endpoints.

Scenario: discovery document and public key exposure.
Tests verify OIDC spec compliance and issuer consistency.
"""

from httpx import AsyncClient
from jose import jwt

# ---------------------------------------------------------------------------
# GET /.well-known/openid-configuration
# ---------------------------------------------------------------------------


class TestWhenGetDiscovery:
    async def test_then_returns_200(self, async_client: AsyncClient):
        resp = await async_client.get("/.well-known/openid-configuration")
        assert resp.status_code == 200

    async def test_then_content_type_is_json(self, async_client: AsyncClient):
        resp = await async_client.get("/.well-known/openid-configuration")
        assert "application/json" in resp.headers["content-type"]

    async def test_then_response_is_not_wrapped_in_envelope(
        self, async_client: AsyncClient
    ):
        """OIDC spec: discovery doc is raw JSON, not the finapp envelope."""
        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()
        # Standard envelope has 'data', 'meta', 'error' keys — discovery must not
        assert "data" not in body
        assert "issuer" in body

    async def test_then_returns_required_oidc_fields(self, async_client: AsyncClient):
        """
        Scenario: downstream client fetches discovery doc
        Given: service is running
        When: GET /.well-known/openid-configuration
        Then: all required OIDC Core fields are present
        """
        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()

        required_fields = [
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "response_types_supported",
            "subject_types_supported",
            "id_token_signing_alg_values_supported",
            "code_challenge_methods_supported",
        ]
        for field in required_fields:
            assert field in body, f"Missing required OIDC field: {field}"

    async def test_then_response_types_supported_contains_code(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()
        assert "code" in body["response_types_supported"]

    async def test_then_code_challenge_methods_supported_is_s256_only(
        self, async_client: AsyncClient
    ):
        """plain method must NOT be listed (security requirement)."""
        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()
        methods = body["code_challenge_methods_supported"]
        assert "S256" in methods
        assert "plain" not in methods

    async def test_then_token_endpoint_auth_methods_supported_contains_none(
        self, async_client: AsyncClient
    ):
        """Public clients use PKCE, not client_secret."""
        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()
        assert "none" in body.get("token_endpoint_auth_methods_supported", ["none"])

    async def test_then_issuer_matches_settings_issuer_url(
        self, async_client: AsyncClient
    ):
        from app.core.config import settings

        resp = await async_client.get("/.well-known/openid-configuration")
        body = resp.json()

        assert body["issuer"] == settings.issuer_url

    async def test_given_issuer_in_discovery_matches_iss_in_issued_access_token(
        self, async_client: AsyncClient, auth_token: str
    ):
        """
        Critical invariant: discovery issuer == token iss claim.
        If these diverge, all downstream token verification breaks.
        """
        from app.core.config import settings

        discovery = (await async_client.get("/.well-known/openid-configuration")).json()
        payload = jwt.decode(
            auth_token,
            settings.auth_public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        assert discovery["issuer"] == payload["iss"]

    async def test_then_cache_control_header_set(self, async_client: AsyncClient):
        """Discovery doc should be cacheable."""
        resp = await async_client.get("/.well-known/openid-configuration")
        assert "cache-control" in resp.headers
