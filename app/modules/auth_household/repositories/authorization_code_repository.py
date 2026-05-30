# app/modules/auth_household/repositories/authorization_code_repository.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth_household.models.authorization_code import AuthorizationCode


class AuthorizationCodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, auth_code: AuthorizationCode) -> AuthorizationCode:
        self.db.add(auth_code)
        await self.db.flush()
        return auth_code

    async def get_by_code_hash(self, code_hash: str) -> AuthorizationCode | None:
        stmt = select(AuthorizationCode).where(AuthorizationCode.code_hash == code_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_id(self, code_id: uuid.UUID) -> None:
        stmt = delete(AuthorizationCode).where(AuthorizationCode.id == code_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def delete_expired(self) -> int:
        now = datetime.now(UTC)
        stmt = delete(AuthorizationCode).where(AuthorizationCode.expires_at < now)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
