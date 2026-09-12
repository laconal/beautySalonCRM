from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.payroll.payroll_model import Payout
from src.schemas.base import PaginationSchema, RequestAllObject

class PayoutRepository(BaseRepository[Payout]):
    async def create(self, payout: Payout) -> Payout:
        self.db.add(payout)
        await self.db.flush()
        await self.db.refresh(payout)
        return payout
    
    async def get_by_ids(self, ids: list[int]) -> list[Payout]:
        result = await self.db.execute(
            select(Payout)
            .where(Payout.id.in_(ids))
            .options(selectinload(Payout.transactions))
        )
        return result.scalars().all()
    
    async def get(self, id: int) -> Payout | None:
        stmt = (select(Payout)
                .where(Payout.id == id)
                .options(
                    selectinload(Payout.payrolls),
                    selectinload(Payout.transactions)
                ))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[Payout], int]:
        count_stmt = select(func.count()).select_from(Payout)
        stmt = select(Payout)
        count_stmt = apply_dynamic_filters(count_stmt, Payout, data.filters)
        stmt = apply_dynamic_filters(stmt, Payout, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = stmt.order_by(Payout.id.desc()).options(selectinload(Payout.payrolls)).offset(offset_value).limit(data.pageSize)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total_items
    
    async def get_by_employee(self, data: PaginationSchema, id: int) -> list[Payout] | None:
        count_stmt = (select(func.count())
            .select_from(Payout)
            .where(Payout.employee_id == id))
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = (
            select(Payout)
            .where(Payout.employee_id == id)
            .offset(offset_value)
            .limit(data.pageSize)
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return items, total_items