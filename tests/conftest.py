"""
Root conftest.py — session-scoped database fixtures and shared helpers.

Requires TEST_DATABASE_URL env var. The Makefile enforces this:
    DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest tests/ --cov=app --cov-fail-under=80 -v
"""

import base64
import hashlib
import secrets
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.session import Base, get_db
from main import app

# ---------------------------------------------------------------------------
# Engine — created once per test session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def engine():
    """
    Creates the full schema once per session using the test database.
    DATABASE_URL is overridden to TEST_DATABASE_URL by the Makefile before
    pytest runs, so settings.database_url already points at the test DB.
    """
    test_engine = create_async_engine(settings.database_url, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test transaction that always rolls back — tests never persist data
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Each test runs inside a transaction that is rolled back on teardown.
    Nothing written in a test ever reaches the database permanently.
    """
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ---------------------------------------------------------------------------
# Override FastAPI's get_db so route handlers use the SAME session
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def override_get_db(db_session: AsyncSession):
    """
    Without this, route handlers open a second connection that commits
    independently — the rollback fixture would have no effect.
    """

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# PKCE helpers (module-level so other conftest files can import them)
# ---------------------------------------------------------------------------


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (verifier, challenge) for S256 PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------------------
# Entity factories
# ---------------------------------------------------------------------------


@pytest.fixture
async def registered_user(async_client: AsyncClient) -> dict:
    """Registers a user via the API and returns the response data dict."""
    resp = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "household_name": "Test Household",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Full PKCE flow fixture — returns a valid access token
# ---------------------------------------------------------------------------


@pytest.fixture
async def auth_token(
    async_client: AsyncClient, registered_user: dict
) -> str:  # noqa: ARG001
    """
    Performs the complete PKCE Authorization Code flow and returns an
    access_token string ready for use as a Bearer header value.
    """
    verifier, challenge = generate_pkce_pair()
    state = "pytest-state-" + str(uuid.uuid4())

    # Step 1 — initiate authorization
    resp = await async_client.get(
        "/v1/auth/authorize",
        params={
            "response_type": "code",
            "client_id": "finapp-web",
            "redirect_uri": "http://localhost:5173/auth/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text

    # Step 2 — submit credentials
    resp = await async_client.post(
        "/v1/auth/authorize/complete",
        json={
            "email": "test@example.com",
            "password": "password123",
            "state": state,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    location = resp.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    # Step 3 — exchange code for tokens
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
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
async def auth_token_with_cookie(
    async_client: AsyncClient, registered_user: dict
) -> dict:  # noqa: ARG001
    """
    Like auth_token but also returns the refresh_token cookie value.
    Returns dict with keys: access_token, id_token, refresh_token_cookie.
    """
    verifier, challenge = generate_pkce_pair()
    state = "pytest-state-" + str(uuid.uuid4())

    resp = await async_client.get(
        "/v1/auth/authorize",
        params={
            "response_type": "code",
            "client_id": "finapp-web",
            "redirect_uri": "http://localhost:5173/auth/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    resp = await async_client.post(
        "/v1/auth/authorize/complete",
        json={
            "email": "test@example.com",
            "password": "password123",
            "state": state,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    code = resp.headers["location"].split("code=")[1].split("&")[0]

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
    return {
        "access_token": body["access_token"],
        "id_token": body["id_token"],
        "refresh_token_cookie": resp.cookies.get("refresh_token"),
    }


# ---------------------------------------------------------------------------
# Admin token — created directly via DB to bypass role restriction
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_token(db_session: AsyncSession) -> str:
    """
    Creates an admin user directly in the database and returns a signed
    access token. Bypasses the API so it does not depend on the register
    endpoint supporting admin-role creation.
    """
    from passlib.context import CryptContext

    from app.modules.auth_household.models.household import Household, HouseholdMember
    from app.modules.auth_household.models.user import User
    from app.modules.auth_household.utils.token import TokenService

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    token_service = TokenService()

    user_id = uuid.uuid4()
    household_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="admin@example.com",
        password_hash=pwd_context.hash("adminpassword"),
        full_name="Admin User",
        is_active=True,
        email_verified=False,
    )
    household = Household(id=household_id, name="Admin Household", region="CA")
    member = HouseholdMember(household_id=household_id, user_id=user_id, role="admin")

    db_session.add_all([user, household, member])
    await db_session.flush()

    return token_service.create_access_token(user=user, memberships=[member])
