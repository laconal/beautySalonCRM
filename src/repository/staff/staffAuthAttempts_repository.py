from sqlalchemy import func, select
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.staff.staffAuthAttempts_model import StaffAuthAttempts
from src.schemas.base import RequestAllObject

class StaffAuthAttemptsRepository(BaseRepository[StaffAuthAttempts]):
    async def create(self, object: StaffAuthAttempts) -> StaffAuthAttempts:
        self.db.add(object)
        await self.db.flush()
        await self.db.refresh(object)
        return object

    async def get_all(self, data: RequestAllObject, staff_id: int) -> tuple[list[StaffAuthAttempts], int]:
        count_stmt = (select(func.count())
            .select_from(StaffAuthAttempts)
            .where(StaffAuthAttempts.staff_id == staff_id)) 
        stmt = select(StaffAuthAttempts).where(StaffAuthAttempts.staff_id == staff_id)
        count_stmt = apply_dynamic_filters(count_stmt, StaffAuthAttempts, data.filters)
        stmt = apply_dynamic_filters(stmt, StaffAuthAttempts, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = (
            stmt.order_by(StaffAuthAttempts.created_at.asc())
            .offset(offset_value)
            .limit(data.pageSize)
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items