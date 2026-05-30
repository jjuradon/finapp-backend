# app/modules/auth_household/repositories/household_member_repository.py
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.auth_household.models.household import HouseholdMember


class HouseholdMemberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, member: HouseholdMember) -> HouseholdMember:
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[HouseholdMember]:
        stmt = select(HouseholdMember).where(HouseholdMember.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
