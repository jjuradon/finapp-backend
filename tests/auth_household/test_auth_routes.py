from fastapi.testclient import TestClient

from main import app  # import FastAPI instance

client = TestClient(app)

# Helper to obtain CSRF token (if needed) – can be a fixture


def get_csrf_header():
    return {"X-CSRF-Token": "test-csrf-token"}


def test_register_user_success():
    payload = {"email": "alice@example.com", "password": "StrongPass!23"}
    response = client.post("/v1/auth/register", json=payload, headers=get_csrf_header())
    assert response.status_code == 201
    # Ensure no sensitive data in response
    assert "password" not in response.json()


def test_register_user_duplicate():
    payload = {"email": "alice@example.com", "password": "StrongPass!23"}
    response = client.post("/v1/auth/register", json=payload, headers=get_csrf_header())
    assert response.status_code == 400
    assert response.json()["detail"] == "User already exists"


# PKCE Authorization flow – start
def test_authorize_start():
    payload = {
        "client_id": "my-client",
        "code_challenge": "abcdef",
        "code_challenge_method": "S256",
        "redirect_uri": "https://frontend.example.com/callback",
        "response_type": "code",
        "scope": "openid profile",
        "state": "xyz",
    }
    response = client.post(
        "/v1/auth/authorize", json=payload, headers=get_csrf_header()
    )
    assert response.status_code == 302  # redirects to login page
    assert "Location" in response.headers


# Complete PKCE exchange
def test_authorize_complete_success():
    # Simulate that the user has authenticated and has a valid code verifier
    params = {
        "code": "authcode123",
        "code_verifier": "validverifier",
    }
    response = client.get("/v1/auth/authorize/complete", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "id_token" in data
    # Refresh token cookie checks
    refresh_cookie = response.cookies.get("__Host-refresh_token")
    assert refresh_cookie is not None
    # Verify cookie flags (HttpOnly, Secure, SameSite)
    cookie_header = response.headers.get("set-cookie")
    assert (
        "HttpOnly" in cookie_header
        and "Secure" in cookie_header
        and "SameSite=Strict" in cookie_header
    )


def test_token_endpoint_invalid_code():
    payload = {
        "grant_type": "authorization_code",
        "code": "badcode",
        "redirect_uri": "https://frontend.example.com/callback",
    }
    response = client.post("/v1/auth/token", json=payload, headers=get_csrf_header())
    assert response.status_code == 400


# Refresh token flow
def test_refresh_success():
    # Assume a valid refresh token cookie from previous step
    client.cookies.set("__Host-refresh_token", "valid-refresh-token")
    response = client.post("/v1/auth/refresh", headers=get_csrf_header())
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # New refresh token rotation
    new_cookie = response.cookies.get("__Host-refresh_token")
    assert new_cookie != "valid-refresh-token"


# Userinfo endpoint
def test_userinfo_success():
    token = "valid-access-token"
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/auth/userinfo", headers=headers)
    assert response.status_code == 200
    assert "sub" in response.json()


# Logout endpoint
def test_logout_revokes():
    client.cookies.set("__Host-refresh_token", "valid-refresh-token")
    response = client.post("/v1/auth/logout", headers=get_csrf_header())
    assert response.status_code == 200
    # Cookie cleared
    assert "__Host-refresh_token=;" in response.headers.get("set-cookie", "")
    # Subsequent refresh should fail
    client.cookies.set("__Host-refresh_token", "valid-refresh-token")
    resp = client.post("/v1/auth/refresh", headers=get_csrf_header())
    assert resp.status_code == 401
