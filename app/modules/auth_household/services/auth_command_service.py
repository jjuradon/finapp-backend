# app/modules/auth_household/services/auth_command_service.py
import base64
import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth_household.models.authorization_code import AuthorizationCode
from app.modules.auth_household.models.household import Household, HouseholdMember
from app.modules.auth_household.models.refresh_token import RefreshToken
from app.modules.auth_household.models.user import User
from app.modules.auth_household.repositories.authorization_code_repository import (
    AuthorizationCodeRepository,
)
from app.modules.auth_household.repositories.household_member_repository import (
    HouseholdMemberRepository,
)
from app.modules.auth_household.repositories.household_repository import (
    HouseholdRepository,
)
from app.modules.auth_household.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.auth_household.repositories.user_repository import UserRepository
from app.modules.auth_household.schemas.auth import (
    AuthorizeParams,
    CompleteAuthSchema,
    RegisterSchema,
    TokenRequestParams,
    TokenResponse,
    UserCreatedSchema,
)
from app.modules.auth_household.utils.oidc_clients import OIDCClientRegistry
from app.modules.auth_household.utils.oidc_provider import LocalCredentialProvider
from app.modules.auth_household.utils.rate_limiter import RateLimiter, redis_client
from app.modules.auth_household.utils.token import TokenService
from app.shared.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    ValidationError,
)


class AuthCommandService:
    def __init__(self, db: AsyncSession, redis=redis_client):
        self.db = db
        self.redis = redis
        self.user_repo = UserRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.member_repo = HouseholdMemberRepository(db)
        self.code_repo = AuthorizationCodeRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.credential_provider = LocalCredentialProvider(self.user_repo)
        self.client_registry = OIDCClientRegistry()
        self.rate_limiter = RateLimiter(self.redis)

    async def register(self, payload: RegisterSchema) -> UserCreatedSchema:
        # Check email uniqueness
        existing_user = await self.user_repo.get_by_email(payload.email)
        if existing_user:
            raise ConflictError("Email already registered")

        # Create user
        hashed_pwd = self.credential_provider.hash_password(payload.password)
        user = User(
            email=payload.email,
            password_hash=hashed_pwd,
            full_name=payload.full_name,
            is_active=True,
            email_verified=False,
        )
        user = await self.user_repo.create(user)

        # Create household
        household = Household(
            name=payload.household_name,
            region="US",
        )
        household = await self.household_repo.create(household)

        # Link user to household as owner
        member = HouseholdMember(
            household_id=household.id,
            user_id=user.id,
            role="owner",
        )
        await self.member_repo.create(member)
        await self.db.commit()

        return UserCreatedSchema(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            household_id=household.id,
            role="owner",
        )

    async def start_authorization(self, params: AuthorizeParams) -> str:
        # Validate params
        if params.response_type != "code":
            raise ValidationError("Unsupported response type")
        if params.code_challenge_method != "S256":
            raise ValidationError("Code challenge method S256 is required")

        client = self.client_registry.get_client(params.client_id)
        if not client:
            raise AuthenticationError("Client not registered")

        if not self.client_registry.validate_redirect_uri(
            params.client_id, params.redirect_uri
        ):
            raise ValidationError("Invalid redirect URI")

        # Save PKCE state in Redis
        pkce_data = {
            "code_challenge": params.code_challenge,
            "client_id": params.client_id,
            "redirect_uri": params.redirect_uri,
            "scope": params.scope or "",
        }
        key = f"finapp:auth:pkce:{params.state}"
        await self.redis.set(key, json.dumps(pkce_data), ex=600)  # 10 min TTL

        # Redirect to frontend login page
        return f"{settings.frontend_login_url}?state={params.state}"

    async def complete_authorization(self, payload: CompleteAuthSchema) -> str:
        # Read PKCE state from Redis
        key = f"finapp:auth:pkce:{payload.state}"
        pkce_raw = await self.redis.get(key)
        if not pkce_raw:
            raise ValidationError("Invalid or expired state")
        pkce_data = json.loads(pkce_raw)

        # Find user first to perform rate limit lockout check
        user = await self.user_repo.get_by_email(payload.email)
        user_id = (
            user.id if user else uuid.uuid4()
        )  # Dummy user_id for lockout tracker if user not found

        # Check lockout
        is_locked, locked_until = await self.rate_limiter.is_user_locked(user_id)
        if is_locked:
            raise AccountLockedError("Account locked", locked_until=locked_until)

        try:
            claim = await self.credential_provider.verify_identity(
                email=payload.email, password=payload.password
            )
            # Reset failure counter on success
            await self.rate_limiter.reset_failures(user_id)
        except AuthenticationError:
            # Record failure and check if locked
            is_locked, locked_until = await self.rate_limiter.record_login_failure(
                user_id
            )
            if is_locked:
                raise AccountLockedError(
                    "Account locked", locked_until=locked_until
                ) from None
            raise AuthenticationError("Invalid credentials") from None

        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        code_hash = TokenService.hash_token(auth_code)
        expires_at = datetime.now(UTC) + timedelta(
            seconds=settings.authorization_code_ttl_seconds
        )

        # Save to database
        db_code = AuthorizationCode(
            code_hash=code_hash,
            code_challenge=pkce_data["code_challenge"],
            code_challenge_method="S256",
            client_id=pkce_data["client_id"],
            redirect_uri=pkce_data["redirect_uri"],
            user_id=uuid.UUID(claim.sub),
            scope=pkce_data["scope"],
            expires_at=expires_at,
        )
        await self.code_repo.create(db_code)
        await self.db.commit()

        # Delete PKCE state
        await self.redis.delete(key)

        return f"{pkce_data['redirect_uri']}?code={auth_code}&state={payload.state}"

    async def exchange_code(
        self, params: TokenRequestParams
    ) -> tuple[TokenResponse, str]:
        # Validate request parameters
        if params.grant_type != "authorization_code":
            raise ValidationError("Unsupported grant type")

        code_hash = TokenService.hash_token(params.code)
        auth_code_row = await self.code_repo.get_by_code_hash(code_hash)
        if not auth_code_row:
            raise AuthenticationError("Invalid or expired authorization code")

        # Check expiry
        now = datetime.now(UTC)
        if auth_code_row.expires_at.replace(tzinfo=UTC) < now:
            await self.code_repo.delete_by_id(auth_code_row.id)
            await self.db.commit()
            raise AuthenticationError("Authorization code expired")

        # Validate client_id and redirect_uri match
        if auth_code_row.client_id != params.client_id:
            raise ValidationError("Client mismatch")
        if auth_code_row.redirect_uri != params.redirect_uri:
            raise ValidationError("Redirect URI mismatch")

        # Verify code verifier
        challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(params.code_verifier.encode()).digest()
            )
            .rstrip(b"=")
            .decode()
        )

        if challenge != auth_code_row.code_challenge:
            raise ValidationError("Code verifier mismatch")

        # Delete authorization code immediately (single-use)
        await self.code_repo.delete_by_id(auth_code_row.id)

        # Get User and Household Member roles
        user = await self.user_repo.get_by_id(auth_code_row.user_id)
        if not user:
            await self.db.commit()
            raise AuthenticationError("User not found")

        memberships = await self.member_repo.get_by_user_id(user.id)

        # Load household names
        household_names = {}
        for m in memberships:
            h = await self.household_repo.get_by_id(m.household_id)
            if h:
                household_names[m.household_id] = h.name

        # Create tokens
        access_token = TokenService.create_access_token(
            user, memberships, household_names
        )
        id_token = TokenService.create_id_token(user, params.client_id)

        raw_refresh = TokenService.generate_refresh_token()
        refresh_hash = TokenService.hash_token(raw_refresh)

        refresh_expiry = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_ttl_days
        )

        # Insert RefreshToken model
        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=uuid.uuid4(),
            expires_at=refresh_expiry,
        )
        await self.token_repo.create(db_refresh)
        await self.db.commit()

        response = TokenResponse(
            access_token=access_token,
            id_token=id_token,
            expires_in=settings.access_token_ttl_seconds,
        )
        return response, raw_refresh

    async def refresh_tokens(self, refresh_token: str) -> tuple[TokenResponse, str]:
        token_hash = TokenService.hash_token(refresh_token)
        db_token = await self.token_repo.get_by_hash(token_hash)
        if not db_token:
            raise AuthenticationError("Invalid refresh token")

        # Check family reuse
        if db_token.is_revoked or db_token.is_family_revoked:
            await self.token_repo.revoke_family(db_token.family_id)
            await self.db.commit()
            raise AuthenticationError("Refresh token family reused or revoked")

        # Check expiry
        now = datetime.now(UTC)
        if db_token.expires_at.replace(tzinfo=UTC) < now:
            db_token.is_revoked = True
            await self.db.commit()
            raise AuthenticationError("Refresh token expired")

        # Mark current token as revoked
        db_token.is_revoked = True

        # Fetch user
        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user:
            await self.db.commit()
            raise AuthenticationError("User not found")

        memberships = await self.member_repo.get_by_user_id(user.id)
        household_names = {}
        for m in memberships:
            h = await self.household_repo.get_by_id(m.household_id)
            if h:
                household_names[m.household_id] = h.name

        access_token = TokenService.create_access_token(
            user, memberships, household_names
        )
        id_token = TokenService.create_id_token(user, "finapp-web")

        new_raw_refresh = TokenService.generate_refresh_token()
        new_refresh_hash = TokenService.hash_token(new_raw_refresh)

        refresh_expiry = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_ttl_days
        )

        new_db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_hash,
            family_id=db_token.family_id,
            expires_at=refresh_expiry,
        )
        await self.token_repo.create(new_db_refresh)
        await self.db.commit()

        response = TokenResponse(
            access_token=access_token,
            id_token=id_token,
            expires_in=settings.access_token_ttl_seconds,
        )
        return response, new_raw_refresh

    async def logout(self, user_id: uuid.UUID, jti: str, token_exp: datetime) -> None:
        # Blacklist access token
        key = f"finapp:auth:blacklist:{jti}"
        now = datetime.now(UTC)
        remaining = int((token_exp - now).total_seconds())
        if remaining > 0:
            await self.redis.set(key, "blacklisted", ex=remaining)

        # Revoke refresh token families
        await self.token_repo.revoke_all_for_user(user_id)
        await self.db.commit()
