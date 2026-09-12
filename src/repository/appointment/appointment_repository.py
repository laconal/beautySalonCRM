from datetime import datetime, timedelta

from sqlalchemy import Row, and_, case, func, select
from sqlalchemy.orm import selectinload
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.appointment.appointment_model import Appointment, AppointmentCancelledReason, AppointmentRecords, AppointmentServices, AppointmentStatus
from src.schemas.analytics.request import GetReportWithFilters
from src.schemas.base import PaginationSchema, RequestAllObject
from src.schemas.appointment.create import AppointmentCreateSchema

class AppointmentRepository(BaseRepository[Appointment]):
    async def create(self, appointment: AppointmentCreateSchema, price_info: list[list[dict]]) -> Appointment:
        db_appointment = Appointment(
            client_id=appointment.client_id,
            start_time_est=appointment.start_time_est,
            end_time_est=appointment.end_time_est,
            notes=appointment.notes,
            records=[
                AppointmentRecords(
                    employee_id=record_data.employee_id,
                    services=[
                        AppointmentServices(
                            service_id=srv.service_id,
                            material_id = srv.material_id,
                            quantity = srv.quantity,
                            base_price = info["base_price"],
                            final_price = info["final_price"],
                            promotion_id = info["promotion_id"],
                            price_changed_reason = srv.price_changed_reason,
                            notes = srv.notes
                        )
                        for srv, info in zip(record_data.services, record_info)
                    ]
                )
                for record_data, record_info in zip((appointment.records or []), price_info)
            ]
        )

        self.db.add(db_appointment)
        await self.db.flush()
        await self.db.refresh(db_appointment)

        stmt = (
            select(Appointment)
            .where(Appointment.id == db_appointment.id)
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.service),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.material)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar()
    
    async def get_by_ids(self, ids: list[int]) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.id.in_(ids))
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.service),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.material)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get(self, id: int) -> Appointment | None:
        stmt = (
            select(Appointment)
            .where(Appointment.id == id)
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.service),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.material)
            )
            .execution_options(populate_existing = True)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[Appointment], int]:
        count_stmt = select(func.count()).select_from(Appointment)
        stmt = select(Appointment)
        count_stmt = apply_dynamic_filters(count_stmt, Appointment, data.filters)
        stmt = apply_dynamic_filters(stmt, Appointment, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = (stmt
                .options(
                    selectinload(Appointment.client),
                    selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                    selectinload(Appointment.records)
                        .selectinload(AppointmentRecords.services)
                        .selectinload(AppointmentServices.service),
                    selectinload(Appointment.records)
                        .selectinload(AppointmentRecords.services)
                        .selectinload(AppointmentServices.material)
                )
                .order_by(Appointment.id.desc())
                .offset(offset_value)
                .limit(data.pageSize))
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items

    async def client_has_overlap(self, clientID: int, start: datetime, end: datetime) -> bool:
        stmt = select(Appointment).where(
                Appointment.client_id == clientID,
                Appointment.start_time_est < end,
                Appointment.end_time_est > start,
                Appointment.status != AppointmentStatus.CANCELLED,
                Appointment.archived.is_(False)
            )
        result = await self.db.execute(stmt)
        return result.first() is not None
    
    async def get_by_client(self, data: PaginationSchema, id: int) -> tuple[list[Appointment], int]:
        count_stmt = (select(func.count())
            .select_from(Appointment)
            .where(Appointment.client_id == id)
            )
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = (
            select(Appointment)
            .where(Appointment.client_id == id)
            .order_by(Appointment.id.desc())
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.service),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.material)
            )
            .offset(offset_value)
            .limit(data.pageSize)
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items
    
    async def get_by_employee(self, data: PaginationSchema, id: int) -> tuple[list[Appointment], int]:
        baseStmt = (
            select(Appointment)
            .join(Appointment.records)
            .where(AppointmentRecords.employee_id == id)
        )

        countStmt = (
            select(func.count(Appointment.id))
            .join(Appointment.records)
            .where(AppointmentRecords.employee_id == id)
        )
        total_items = await self.db.scalar(countStmt) or 0

        offset_value = (data.page - 1) * data.pageSize
        stmt = (
            baseStmt
            .order_by(Appointment.id.desc())
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.records).selectinload(AppointmentRecords.employee),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.service),
                selectinload(Appointment.records)
                    .selectinload(AppointmentRecords.services)
                    .selectinload(AppointmentServices.material)
            )
            .offset(offset_value)
            .limit(data.pageSize)
        )

        result = await self.db.execute(stmt)
        items = result.scalars().unique().all()
        return items, total_items

    async def get_analytics(self, data: GetReportWithFilters) -> Row:
        stmt = (
            select(
                func.count(Appointment.id).label("amount"),
                func.sum(
                    case(
                        (Appointment.status == AppointmentStatus.FINISHED, 1), 
                        else_ = 0)).label("finished"),
                func.sum(
                    case(
                        (Appointment.status == AppointmentStatus.CANCELLED, 1), 
                        else_ = 0)).label("cancelled"),
                func.sum(
                    case(
                        (and_(
                            Appointment.status == AppointmentStatus.CANCELLED,
                            Appointment.status == AppointmentCancelledReason.CLIENT_CANCELLED
                        ), 1), 
                        else_ = 0)).label("absent")
            )
            .where(and_(
                Appointment.created_at >= data.start_date,
                Appointment.created_at < data.end_date + timedelta(days=1),
                Appointment.tenant_id == data.branch_id
            ))
            .execution_options(skip_tenant_filter = True)
        )

        result = await self.db.execute(stmt)
        return result.one()