# app/modules/auth_household/utils/token.py
import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA256, Hash
from jose import jwt

from app.core.config import settings
from app.modules.auth_household.models.household import HouseholdMember
from app.modules.auth_household.models.user import User
from app.modules.auth_household.schemas.auth import TokenPayload
from app.shared.exceptions import AuthenticationError


class TokenService:
    @staticmethod
    def generate_refresh_token() -> str:
        return secrets.token_urlsafe(64)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def public_key_to_jwks(public_key_pem: str) -> dict:
        """Converts RSA public key to RFC 7517 JWKS format."""
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            numbers = pub_key.public_numbers()

            def to_base64url(val: int) -> str:
                byte_len = (val.bit_length() + 7) // 8
                val_bytes = val.to_bytes(byte_len, byteorder="big")
                return base64.urlsafe_b64encode(val_bytes).decode("utf-8").rstrip("=")

            n_str = to_base64url(numbers.n)
            e_str = to_base64url(numbers.e)

            der = pub_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            digest = Hash(SHA256())
            digest.update(der)
            kid = digest.finalize().hex()

            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "alg": "RS256",
                        "kid": kid,
                        "n": n_str,
                        "e": e_str,
                    }
                ]
            }
        except Exception as e:
            raise ValueError(f"Failed to parse public key for JWKS: {e}") from e

    @staticmethod
    def get_key_id(public_key_pem: str) -> str:
        """Helper to get kid for ID token header."""
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            der = pub_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            digest = Hash(SHA256())
            digest.update(der)
            return digest.finalize().hex()
        except Exception:
            return "default-kid"

    @classmethod
    def create_id_token(cls, user: User, client_id: str) -> str:
        now = int(datetime.now(UTC).timestamp())
        kid = cls.get_key_id(settings.auth_public_key)

        payload = {
            "iss": settings.issuer_url,
            "sub": str(user.id),
            "aud": client_id,
            "iat": now,
            "exp": now + settings.id_token_ttl_seconds,
            "email": user.email,
            "name": user.full_name,
            "email_verified": user.email_verified,
        }

        headers = {"kid": kid}
        return jwt.encode(
            payload, settings.auth_private_key, algorithm="RS256", headers=headers
        )

    @classmethod
    def create_access_token(
        cls,
        user: User,
        memberships: list[HouseholdMember],
        household_names: dict[uuid.UUID, str] = None,
    ) -> str:
        if household_names is None:
            household_names = {}

        now = int(datetime.now(UTC).timestamp())
        kid = cls.get_key_id(settings.auth_public_key)

        # Build roles and households claims
        roles = list({m.role for m in memberships})
        households_claim = []
        for m in memberships:
            households_claim.append(
                {
                    "id": str(m.household_id),
                    "name": household_names.get(m.household_id, "Household"),
                    "role": m.role,
                }
            )

        payload = {
            "iss": settings.issuer_url,
            "sub": str(user.id),
            "email": user.email,
            "roles": roles,
            "households": households_claim,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + settings.access_token_ttl_seconds,
        }

        headers = {"kid": kid}
        return jwt.encode(
            payload, settings.auth_private_key, algorithm="RS256", headers=headers
        )

    @staticmethod
    def decode_access_token(token: str) -> TokenPayload:
        try:
            # RS256 algorithm is hardcoded here, never derived from token header
            payload = jwt.decode(
                token,
                settings.auth_public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            return TokenPayload(**payload)
        except Exception as e:
            raise AuthenticationError(f"Invalid access token: {e}") from e
