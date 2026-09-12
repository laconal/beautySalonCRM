from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.appointment.appointment_model import Appointment, AppointmentRecords, AppointmentServices, AppointmentStatus
from src.schemas.appointment.create import AppointmentRecordsCreateSchema
from src.schemas.base import RequestAllObject

class AppointmentRecordsRepository(BaseRepository[AppointmentRecords]):
    async def create(self, appointmentRecord: AppointmentRecordsCreateSchema, price_info: list[dict]) -> AppointmentRecords:
        db_services = [
            AppointmentServices(
                service_id = service.service_id,
                material_id = service.material_id,
                quantity = service.quantity,
                base_price = info["base_price"],
                final_price = info["final_price"],
                promotion_id = info["promotion_id"],
                price_changed_reason = service.price_changed_reason,
                notes = service.notes
            )
            for service, info in zip(appointmentRecord.services, price_info)
        ]

        db_appointmentRecord = AppointmentRecords(
            appointment_id = appointmentRecord.appointment_id,
            employee_id = appointmentRecord.employee_id,
            services = db_services
        )

        self.db.add(db_appointmentRecord)
        await self.db.flush()
        await self.db.refresh(db_appointmentRecord)
        return db_appointmentRecord
    
    async def get_by_ids(self, ids: list[int]) -> list[AppointmentRecords]:
        stmt = (
            select(AppointmentRecords)
            .where(AppointmentRecords.id.in_(ids))
            .options(selectinload(AppointmentRecords.services))
        )
        return stmt.scalars().all()
    
    async def get(self, id: int) -> AppointmentRecords | None:
        stmt = (
            select(AppointmentRecords)
            .where(AppointmentRecords.id == id)
            .options(selectinload(AppointmentRecords.services))
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[AppointmentRecords], int]:
        count_stmt = select(func.count()).select_from(AppointmentRecords)
        stmt = select(AppointmentRecords)
        count_stmt = apply_dynamic_filters(count_stmt, AppointmentRecords, data.filters)
        stmt = apply_dynamic_filters(stmt, AppointmentRecords, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = stmt.options(selectinload(AppointmentRecords.services)).offset(offset_value).limit(data.pageSize)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items

    async def employee_has_overlap(self, employeeID: int,
                                   start: datetime,
                                   end: datetime,
                                   lock: bool = False) -> bool:
        stmt = (
            select(AppointmentRecords.id)
            .join(Appointment, AppointmentRecords.appointment_id == Appointment.id)
            .where(
                AppointmentRecords.employee_id == employeeID,
                Appointment.status != AppointmentStatus.CANCELLED,
                Appointment.start_time_est < end,
                Appointment.end_time_est > start
            )
        )

        if lock: stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        return result.first() is not None