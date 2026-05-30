"""
Integration tests for the get_current_user and require_role shared dependencies.

These dependencies are the permanent contract every subsequent epic imports.
Their behaviour must be verified comprehensively here.

Tests use a purpose-built /v1/auth/test/protected endpoint that is registered
only in the test environment and requires a specific role.
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fixture: register a protected test route before tests run
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def register_protected_test_routes():
    """
    Adds two routes to the FastAPI app only for this test module:
      GET /v1/test/user-only   — requires role 'owner' or 'member'
      GET /v1/test/admin-only  — requires role 'admin'

    Routes are removed after the test session to avoid contaminating others.
    """
    from fastapi.routing import APIRoute

    from main import app

    async def _user_route(current_user, _):
        return {"status": "ok", "user": current_user.sub}

    async def _admin_route(current_user, _):
        return {"status": "ok", "user": current_user.sub}

    user_route = APIRoute(
        path="/v1/test/user-only",
        endpoint=_user_route,
        methods=["GET"],
        name="test_user_only",
    )
    admin_route = APIRoute(
        path="/v1/test/admin-only",
        endpoint=_admin_route,
        methods=["GET"],
        name="test_admin_only",
    )

    app.router.routes.append(user_route)
    app.router.routes.append(admin_route)
    app.router.route_class = app.router.route_class  # trigger rebuild

    yield

    # Cleanup
    app.router.routes[:] = [
        r
        for r in app.router.routes
        if getattr(r, "name", None) not in ("test_user_only", "test_admin_only")
    ]


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGivenValidTokenWhenAccessingProtectedRoute:
    async def test_then_returns_200(self, async_client: AsyncClient, auth_token: str):
        """
        Scenario: authenticated request with correct role
        Given: valid access token with role 'owner'
        When: GET /v1/test/user-only
        Then: 200
        """
        resp = await async_client.get(
            "/v1/test/user-only",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200


class TestGivenNoTokenWhenAccessingProtectedRoute:
    async def test_then_returns_401(self, async_client: AsyncClient):
        """
        Scenario: missing token
        Given: no Authorization header
        When: GET /v1/test/user-only
        Then: 401 (not 403)
        """
        resp = await async_client.get("/v1/test/user-only")
        assert resp.status_code == 401

    async def test_then_error_is_authentication_failed_not_forbidden(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get("/v1/test/user-only")
        # Must be 401, never 403, for missing token
        assert resp.status_code == 401


class TestGivenExpiredTokenWhenAccessingProtectedRoute:
    async def test_then_returns_401(self, async_client: AsyncClient):
        """Expired token must return 401, not 403."""
        import time
        import uuid

        from cryptography.hazmat.primitives.serialization import load_pem_private_key
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
        private_key = load_pem_private_key(
            settings.auth_private_key.replace("\\n", "\n").encode(), password=None
        )
        expired_token = jose_jwt.encode(expired_payload, private_key, algorithm="RS256")

        resp = await async_client.get(
            "/v1/test/user-only",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401


class TestGivenTamperedTokenWhenAccessingProtectedRoute:
    async def test_then_returns_401(self, async_client: AsyncClient, auth_token: str):
        parts = auth_token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        tampered = ".".join(parts)

        resp = await async_client.get(
            "/v1/test/user-only",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401


class TestGivenBlacklistedTokenWhenAccessingProtectedRoute:
    async def test_then_returns_401(self, async_client: AsyncClient, auth_token: str):
        """Token blacklisted via logout must return 401 on subsequent requests."""
        # Blacklist the token via logout
        await async_client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Subsequent request with same token
        resp = await async_client.get(
            "/v1/test/user-only",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------


class TestGivenWrongRoleWhenAccessingProtectedRoute:
    async def test_then_returns_403(self, async_client: AsyncClient, auth_token: str):
        """
        Scenario: valid token, wrong role
        Given: user has role 'owner', route requires 'admin'
        When: GET /v1/test/admin-only
        Then: 403 (not 401)
        """
        resp = await async_client.get(
            "/v1/test/admin-only",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 403


class TestGivenCorrectRoleWhenAccessingAdminRoute:
    async def test_then_returns_200(self, async_client: AsyncClient, admin_token: str):
        """
        Scenario: admin accessing admin-only route
        Given: valid token with role 'admin'
        When: GET /v1/test/admin-only
        Then: 200
        """
        resp = await async_client.get(
            "/v1/test/admin-only",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200


class TestGivenNoTokenWhenAccessingAdminRoute:
    async def test_then_returns_401_not_403(self, async_client: AsyncClient):
        """
        Missing token must always return 401, even on admin-only routes.
        403 is only for valid tokens with insufficient roles.
        """
        resp = await async_client.get("/v1/test/admin-only")
        assert resp.status_code == 401
