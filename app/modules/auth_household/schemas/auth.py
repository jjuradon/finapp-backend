# app/modules/auth_household/schemas/auth.py
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterSchema(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(max_length=100)
    household_name: str = Field(max_length=100)


class UserCreatedSchema(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    household_id: uuid.UUID
    role: str


class AuthorizeParams(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    state: str
    scope: str | None = None


class CompleteAuthSchema(BaseModel):
    email: EmailStr
    password: str
    state: str


class TokenRequestParams(BaseModel):
    grant_type: Literal["authorization_code"]
    code: str
    code_verifier: str
    client_id: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int


class UserinfoSchema(BaseModel):
    sub: str
    email: str
    name: str
    email_verified: bool
    roles: list[str]
    households: list[dict]  # list of {id: str, name: str, role: str}


class DiscoverySchema(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    response_types_supported: list[str]
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    scopes_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    code_challenge_methods_supported: list[str]
    claims_supported: list[str]


class JWKKey(BaseModel):
    kty: str
    use: str
    alg: str
    kid: str
    n: str
    e: str


class JWKSSchema(BaseModel):
    keys: list[JWKKey]


class TokenPayload(BaseModel):
    iss: str
    sub: str
    email: str
    roles: list[str]
    households: list[dict]
    jti: str
    exp: int
    iat: int
