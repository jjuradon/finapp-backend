# app/modules/auth_household/utils/oidc_provider.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

from passlib.context import CryptContext

from app.modules.auth_household.repositories.user_repository import UserRepository
from app.shared.exceptions import AuthenticationError

# Configure CryptContext with bcrypt rounds=12
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# Timing-safe dummy hash for user-not-found scenario
DUMMY_HASH = "$2b$12$N9qo8uLOqpGC12Z5Q5GPxeM0Mc.5R.Qo711lM52kF8p92S8x2nOum"


@dataclass
class IdentityClaim:
    sub: str  # stable unique identifier from the provider
    email: str
    name: str
    email_verified: bool


class OIDCProvider(ABC):
    @abstractmethod
    async def verify_identity(self, **credentials) -> IdentityClaim:
        """
        Verify the presented credentials and return a verified identity claim.
        Phase 1: credentials = {email, password}
        Phase 2: credentials = {id_token} from Google/Facebook/etc.
        Raises AuthenticationError on failure.
        """
        pass


class LocalCredentialProvider(OIDCProvider):
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def verify_identity(self, email: str, password: str) -> IdentityClaim:
        user = await self.user_repo.get_by_email(email)
        if user is None:
            # timing-safe check
            pwd_context.verify(password, DUMMY_HASH)
            raise AuthenticationError("Invalid credentials")

        if not user.password_hash or not pwd_context.verify(
            password, user.password_hash
        ):
            raise AuthenticationError("Invalid credentials")

        return IdentityClaim(
            sub=str(user.id),
            email=user.email,
            name=user.full_name,
            email_verified=user.email_verified,
        )

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
