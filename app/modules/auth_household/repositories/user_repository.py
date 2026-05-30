# app/modules/auth_household/repositories/user_repository.py
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.auth_household.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_memberships(self, user_id: uuid.UUID) -> User | None:
        # Since we don't have relationships on the User model, we can simply fetch the User
        # and let the caller fetch memberships separately, or join if needed.
        # Return User if it exists.
        return await self.db.get(User, user_id)
