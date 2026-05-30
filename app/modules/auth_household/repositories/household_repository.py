# app/modules/auth_household/repositories/household_repository.py
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth_household.models.household import Household


class HouseholdRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, household: Household) -> Household:
        self.db.add(household)
        await self.db.flush()
        return household

    async def get_by_id(self, household_id: uuid.UUID) -> Household | None:
        return await self.db.get(Household, household_id)
