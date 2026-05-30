# app/modules/auth_household/services/auth_query_service.py
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth_household.repositories.household_member_repository import (
    HouseholdMemberRepository,
)
from app.modules.auth_household.repositories.household_repository import (
    HouseholdRepository,
)
from app.modules.auth_household.repositories.user_repository import UserRepository
from app.modules.auth_household.schemas.auth import (
    DiscoverySchema,
    JWKSSchema,
    UserinfoSchema,
)
from app.modules.auth_household.utils.token import TokenService
from app.shared.exceptions import NotFoundError


class AuthQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.member_repo = HouseholdMemberRepository(db)

    async def get_userinfo(self, user_id: uuid.UUID) -> UserinfoSchema:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        memberships = await self.member_repo.get_by_user_id(user_id)

        roles = list({m.role for m in memberships})
        households = []
        for m in memberships:
            h = await self.household_repo.get_by_id(m.household_id)
            if h:
                households.append({"id": str(h.id), "name": h.name, "role": m.role})

        return UserinfoSchema(
            sub=str(user.id),
            email=user.email,
            name=user.full_name,
            email_verified=user.email_verified,
            roles=roles,
            households=households,
        )

    @staticmethod
    def get_discovery() -> DiscoverySchema:
        # Build endpoints absolute URLs using settings.issuer_url
        base = settings.issuer_url.rstrip("/")
        return DiscoverySchema(
            issuer=settings.issuer_url,
            authorization_endpoint=f"{base}/v1/auth/authorize",
            token_endpoint=f"{base}/v1/auth/token",
            userinfo_endpoint=f"{base}/v1/auth/userinfo",
            jwks_uri=f"{base}/v1/auth/.well-known/jwks.json",
            response_types_supported=["code"],
            subject_types_supported=["public"],
            id_token_signing_alg_values_supported=["RS256"],
            scopes_supported=["openid", "email", "profile"],
            token_endpoint_auth_methods_supported=["none"],
            code_challenge_methods_supported=["S256"],
            claims_supported=[
                "sub",
                "iss",
                "aud",
                "exp",
                "iat",
                "email",
                "name",
                "email_verified",
                "roles",
                "households",
            ],
        )

    @staticmethod
    def get_jwks() -> JWKSSchema:
        jwks_dict = TokenService.public_key_to_jwks(settings.auth_public_key)
        return JWKSSchema(**jwks_dict)
