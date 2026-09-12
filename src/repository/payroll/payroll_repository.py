from datetime import date
from sqlalchemy import func, select
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.payroll.payroll_model import Payroll, PayrollStatus
from src.schemas.base import PaginationSchema, RequestAllObject

class PayrollRepository(BaseRepository[Payroll]):
    async def create(self, payroll: Payroll) -> Payroll:
        self.db.add(payroll)
        await self.db.flush()
        await self.db.refresh(payroll)
        return payroll
    
    async def get(self, id: int) -> Payroll | None:
        stmt = (select(Payroll).where(Payroll.id == id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_ids(self, ids: list[int], lock: bool = False) -> list[Payroll]:
        stmt = select(Payroll).where(Payroll.id.in_(ids))
        if lock:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[Payroll], int]:
        count_stmt = select(func.count()).select_from(Payroll)
        stmt = select(Payroll)
        count_stmt = apply_dynamic_filters(count_stmt, Payroll, data.filters)
        stmt = apply_dynamic_filters(stmt, Payroll, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = stmt.order_by(Payroll.id.desc()).offset(offset_value).limit(data.pageSize)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items
    
    async def get_by_employee(self, data: PaginationSchema, id: int) -> list[Payroll] | None:
        count_stmt = select(func.count()).select_from(Payroll).where(Payroll.employee_id == id)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = (
            select(Payroll)
            .where(Payroll.employee_id == id)
            .offset(offset_value)
            .limit(data.pageSize)
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return items, total_items
    
    async def get_pendings(self, employee_id: int, 
                           start_date: date | None = None, 
                           end_date: date | None = None, 
                           lock: bool = False) -> list[Payroll]:
        stmt = (select(Payroll)
            .where(
                Payroll.employee_id == employee_id,
                Payroll.status == PayrollStatus.PENDING
            ))

        if start_date and end_date:
            stmt = stmt.where(
                func.date(Payroll.created_at) >= start_date,
                func.date(Payroll.created_at) <= end_date
            )

        if lock:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        return result.scalars().all()