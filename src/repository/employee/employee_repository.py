from datetime import timedelta

from sqlalchemy import Row, and_, case, func, select
from sqlalchemy.orm import joinedload, selectinload
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository.appointment.appointment_model import Appointment, AppointmentRecords, AppointmentServices
from src.repository.employee.employee_model import Employee
from src.schemas.base import RequestAllObject
from src.schemas.analytics.request import GetReportWithFilters

class EmployeeRepository(BaseRepository[Employee]):
    async def create(self, employee: Employee) -> Employee:
        self.db.add(employee)
        await self.db.flush()
        stmt = (
            select(Employee)
            .where(Employee.id == employee.id)
            .options(selectinload(Employee.services))
        )
        result = await self.db.execute(stmt)
        return result.scalar()

    async def get(self, id: int) -> Employee | None:
        stmt = (
            select(Employee)
            .where(Employee.id == id)
            .options(selectinload(Employee.services))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[Employee], int]:
        count_stmt = select(func.count()).select_from(Employee)
        stmt = select(Employee)
        count_stmt = apply_dynamic_filters(count_stmt, Employee, data.filters)
        stmt = apply_dynamic_filters(stmt, Employee, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = stmt.options(selectinload(Employee.services)).order_by(Employee.id.desc()).offset(offset_value).limit(data.pageSize)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items

    async def get_by_ids(self, ids: list[int]) -> list[Employee]:
        result = await self.db.execute(
            select(Employee)
            .where(Employee.id.in_(ids))
            .options(selectinload(Employee.services))
        )
        return result.scalars().all()

    async def lock_for_update(self, ids: list[int]) -> list[Employee]:
        # ordered by id so concurrent callers acquire locks in the same order and never deadlock
        stmt = (
            select(Employee)
            .where(Employee.id.in_(ids))
            .order_by(Employee.id)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_for_export(self) -> list[Employee]:
        stmt = (
            select(Employee)
            .options(
                selectinload(Employee.specialization),
                selectinload(Employee.services),
            )
            .order_by(Employee.id.asc())
        )

        result = await self.db.execute(stmt)
        return result.scalars().unique().all()

    async def get_analytics(self, data: GetReportWithFilters) -> list[Row]:
        services_final_price_sum = func.coalesce(
            func.sum(
                case(
                    (AppointmentServices.service_id.isnot(None), AppointmentServices.final_price),
                    else_ = 0
                )
            ),
            0
        )

        stmt = (
            select(
                Employee.id.label("employee_id"),
                func.concat_ws(' ', Employee.lastname, Employee.firstname, Employee.middlename).label("fullname"),
                func.count(func.distinct(Appointment.id)).label("appointments_amount"),
                func.count(AppointmentServices.id).label("services_amount"),
                services_final_price_sum.label("services_final_price_sum"),
            )
            .select_from(Employee)
            .where(Employee.tenant_id == data.branch_id)
            .outerjoin(
                AppointmentRecords,
                and_(
                    AppointmentRecords.employee_id == Employee.id,
                    AppointmentRecords.tenant_id == data.branch_id
                ),
            )
            .outerjoin(
                Appointment,
                and_(
                    AppointmentRecords.appointment_id == Appointment.id,
                    AppointmentRecords.tenant_id == Appointment.tenant_id,
                    Appointment.paid.is_(True),
                    Appointment.created_at >= data.start_date,
                    Appointment.created_at < data.end_date + timedelta(days = 1),
                    Appointment.tenant_id == data.branch_id
                ),
            )
            .outerjoin(
                AppointmentServices,
                and_(
                    AppointmentServices.appointment_record_id == AppointmentRecords.id,
                    AppointmentServices.tenant_id == AppointmentRecords.tenant_id,
                    AppointmentServices.tenant_id == data.branch_id,
                    Appointment.id.isnot(None),
                ),
            )
            .group_by(Employee.id)
            .order_by(services_final_price_sum.desc())
            .execution_options(skip_tenant_filter = True)
        )
        result = await self.db.execute(stmt)
        return result.all()
