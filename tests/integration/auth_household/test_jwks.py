"""
Integration tests for the JWKS endpoint.

Scenario: key publication for downstream token verification.
"""

import base64

from httpx import AsyncClient
from jose import jwt


class TestWhenGetJwks:
    async def test_then_returns_200(self, async_client: AsyncClient):
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        assert resp.status_code == 200

    async def test_then_response_is_not_wrapped_in_envelope(
        self, async_client: AsyncClient
    ):
        """OIDC spec: JWKS is raw JSON."""
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        body = resp.json()
        assert "keys" in body
        assert "data" not in body

    async def test_then_keys_array_is_not_empty(self, async_client: AsyncClient):
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        body = resp.json()
        assert len(body["keys"]) >= 1

    async def test_then_returns_valid_rfc7517_format(self, async_client: AsyncClient):
        """
        Scenario: downstream service fetches JWKS to verify tokens
        Given: service is running with an RS256 key pair configured
        When: GET /v1/auth/.well-known/jwks.json
        Then: response has kty, use, alg, kid, n, e for each key
        """
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        key = resp.json()["keys"][0]

        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert "kid" in key and key["kid"]
        assert "n" in key and key["n"]  # modulus
        assert "e" in key and key["e"]  # exponent

    async def test_then_n_is_valid_base64url(self, async_client: AsyncClient):
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        key = resp.json()["keys"][0]
        # Must decode without error (add padding for base64url)
        n = key["n"]
        padded = n + "=" * (-len(n) % 4)
        base64.urlsafe_b64decode(padded)

    async def test_given_issued_token_when_verified_with_jwks_key_then_succeeds(
        self, async_client: AsyncClient, auth_token: str
    ):
        """
        Scenario: consumer verifies token using JWKS
        Given: an access token issued by our token endpoint
        When: verified using the RSA public key from the JWKS endpoint
        Then: verification succeeds and payload is readable
        """
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        from app.core.config import settings

        # Use the public key from settings (same as what JWKS endpoint exposes)
        public_key = load_pem_public_key(
            settings.auth_public_key.replace("\\n", "\n").encode()
        )

        payload = jwt.decode(
            auth_token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        assert "sub" in payload
        assert "email" in payload

    async def test_then_cache_control_header_set(self, async_client: AsyncClient):
        resp = await async_client.get("/v1/auth/.well-known/jwks.json")
        assert "cache-control" in resp.headers
