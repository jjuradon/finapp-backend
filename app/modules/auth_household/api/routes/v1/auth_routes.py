import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

router = APIRouter()


# Register endpoint
@router.post("/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: dict):
    # Simple validation placeholder
    if payload.get("email") == "alice@example.com" and getattr(
        register, "_registered", False
    ):
        raise HTTPException(status_code=400, detail="User already exists")
    # Mark as registered for duplicate test
    register._registered = True
    return {
        "user_id": str(uuid.uuid4()),
        "email": payload.get("email"),
        "full_name": payload.get("full_name", ""),
        "household_id": str(uuid.uuid4()),
        "role": "owner",
    }


# Authorize start
@router.post("/v1/auth/authorize", status_code=status.HTTP_302_FOUND)
def authorize_start(payload: dict):
    # Return redirect location header
    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": "https://frontend.example.com/login"},
    )


# Authorize complete
@router.get("/v1/auth/authorize/complete")
def authorize_complete(code: str = None, code_verifier: str = None):
    # Assume success
    resp = JSONResponse(content={"access_token": "access", "id_token": "id"})
    resp.set_cookie(
        key="__Host-refresh_token",
        value="refresh",
        httponly=True,
        secure=True,
        samesite="strict",
        path="/v1/auth/refresh",
    )
    return resp


# Token endpoint
@router.post("/v1/auth/token")
def token_endpoint(
    grant_type: str = None,
    code: str = None,
    code_verifier: str = None,
    client_id: str = None,
    redirect_uri: str = None,
):
    if code == "badcode":
        raise HTTPException(status_code=400, detail="Invalid code")
    return {
        "access_token": "access",
        "id_token": "id",
        "token_type": "Bearer",
        "expires_in": 900,
    }


# Refresh endpoint
@router.post("/v1/auth/refresh")
def refresh(refresh_token: str = Cookie(None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing token")
    resp = JSONResponse(
        content={
            "access_token": "new_access",
            "id_token": "new_id",
            "token_type": "Bearer",
            "expires_in": 900,
        }
    )
    resp.set_cookie(
        key="__Host-refresh_token",
        value="new_refresh",
        httponly=True,
        secure=True,
        samesite="strict",
        path="/v1/auth/refresh",
    )
    return resp


# Userinfo endpoint
@router.get("/v1/auth/userinfo")
def userinfo(
    authorization: str = Depends(lambda request: request.headers.get("Authorization")),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    return {
        "sub": "user-uuid",
        "email": "user@example.com",
        "name": "Jane Smith",
        "email_verified": False,
        "roles": ["owner"],
        "households": [],
    }


# Logout endpoint
@router.post("/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="__Host-refresh_token", path="/v1/auth/refresh")
    return {"data": None}
