from io import BytesIO
import json
import math

from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from src.core.decorators.requireID import require_exists
from src.core.dependencies.context import get_current_tenant_id
from src.core.dependencies.uow import UnitOfWork
from src.core.utils.common import check_branch_belong_to_tenant
from src.exceptions.service_exceptions import ServiceIsArchived, ServiceOneOrMoreNotFound
from src.exceptions.specialization_exceptions import SpecializationIsArchived, SpecializationNotFound
from src.repository.employee.employee_model import Employee
from src.schemas.analytics.employeeResponse import EmployeeAnalyticsBaseResponse, EmployeeAnalyticsResponse
from src.schemas.base import PaginationSchema, RequestAllObject
from src.schemas.employee.create import EmployeeCreateSchema
from src.schemas.employee.update import EmployeeUpdateSchema
from src.services.employee.workSchedule_service import WorkScheduleService
from src.exceptions.employee_exceptions import EmployeeNotFound, EmployeeIsArchived
from src.schemas.analytics.request import GetReportWithFilters

class EmployeeService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, data: EmployeeCreateSchema) -> Employee:
        employee_data = data.model_dump()
        services_ids = employee_data.pop("services_ids", [])
        
        new_employee = Employee(**employee_data)
        
        if services_ids:
            found_services = await self.uow.services.get_by_ids(services_ids)
            if len(found_services) != len(services_ids): raise ServiceOneOrMoreNotFound()
            new_employee.services = found_services

        if data.specialization_id:
            specialization = await self.uow.specializations.get(data.specialization_id)
            if specialization is None: raise SpecializationNotFound(data.specialization_id)
            if specialization.archived: raise SpecializationIsArchived(data.specialization_id, specialization.name)

        result = await self.uow.employees.create(new_employee)
        return await self.uow.employees.get(result.id)
    
    async def get(self, id: int) -> Employee:
        result = await self.uow.employees.get(id)
        if result is None: raise EmployeeNotFound(id) 
        return result
    
    async def update(self, data: EmployeeUpdateSchema) -> Employee:
        checkArchived = await self.uow.employees.get(data.id)
        if checkArchived is None: raise EmployeeNotFound(data.id)
        if checkArchived.archived: raise EmployeeIsArchived(data.id, data.firstname)

        dataDict = data.model_dump(exclude={"id"}, exclude_unset=True)
        if data.services is not None:
            services = []
            if len(data.services) >= 1:
                services = await self.uow.services.get_by_ids(data.services)
                if len(services) != len(data.services): raise ServiceOneOrMoreNotFound()
                for service in services: 
                    if service.archived: raise ServiceIsArchived(service.id, service.name)
            dataDict["services"] = services

        if data.specialization_id is not None:
            specialization = await self.uow.specializations.get(data.specialization_id)
            if specialization is None: raise SpecializationNotFound()
            if specialization.archived: raise SpecializationIsArchived(data.specialization_id, specialization.name)
        
        result = await self.uow.employees.update(data.id, **dataDict)
        return result
    
    async def get_many(self, ids: list[int]) -> list[Employee]:
        return await self.uow.employees.get_by_ids(ids)
    
    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.employees.get_all(data)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    async def delete(self, id: int) -> bool:
        return await self.uow.employees.delete(id)
    
    @require_exists("employees")
    async def get_workSchedules(self, id: int) -> dict:
        result = await self.uow.work_schedules.get_workSchedules(id)
        return {
            "work_schedules": [
                WorkScheduleService._to_response_schedule(schedule)
                for schedule in result["work_schedules"]
            ],
            "absences": result["absences"]
        }
    
    @require_exists("employees")
    async def get_payrolls(self, data: PaginationSchema, id: int) -> dict:
        items, total_items = await self.uow.payrolls.get_by_employee(data, id)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    @require_exists("employees")
    async def get_appointments(self, data: PaginationSchema, id: int) -> dict:
        items, total_items = await self.uow.appointments.get_by_employee(data, id)

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0
        
        return {
            "items": items,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }

    def _export_excel(self, employees: list[dict]):
        wb = Workbook()
        ws = wb.active
        ws.title = "Employees"

        headers = [
            "ID",
            "First name",
            "Last name",
            "Middle name",
            "Phone",
            "Birth date",
            "Active",
            "Specialization",
            "Salary",
            "% Services",
            "% Sales",
            "Services",
            "Notes",
        ]

        ws.append(headers)

        for emp in employees:
            ws.append([
                emp["id"],
                emp["firstname"],
                emp["lastname"],
                emp["middlename"],
                emp["phone"],
                emp["birth_date"],
                "Yes" if emp["active"] else "No",
                emp["specialization"],
                emp["salary_fixed"],
                emp["percent_from_services"],
                emp["percent_from_sales"],
                ", ".join(emp["services"]),
                emp["notes"],
            ])

        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)

        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="employees.xlsx"'
            }, 
        )  

    def _export_json(self, data: list[dict]):
        stream = BytesIO()

        stream.write(
            json.dumps(
                data,
                ensure_ascii=False,  # preserve Unicode
                indent=2,
            ).encode("utf-8")
        )
        stream.seek(0)

        return StreamingResponse(
            stream,
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="employees.json"',
            },
        )

    async def export(self, format: str):
        employees = await self.uow.employees.get_all_for_export()

        data = [
            {
                "id": e.id,
                "firstname": e.firstname,
                "lastname": e.lastname,
                "middlename": e.middlename,
                "phone": e.phone,
                "birth_date": e.birth_date.isoformat(),
                "active": e.active,
                "specialization": (
                    e.specialization.name
                    if e.specialization
                    else None
                ),
                "salary_fixed": e.salary_fixed,
                "percent_from_services": e.percent_from_services,
                "percent_from_sales": e.percent_from_sales,
                "services": [s.name for s in e.services],
                "notes": e.notes,
            }
            for e in employees
        ]

        if format == "json":
            return self._export_json(data)

        return self._export_excel(data)

    async def get_analytics(self, data: GetReportWithFilters) -> EmployeeAnalyticsResponse:
        branchID: int
        if data.branch_id is not None:
            await check_branch_belong_to_tenant(self.uow, data.branch_id)
            branchID = data.branch_id
        else: branchID = get_current_tenant_id()

        data.branch_id = branchID

        rows = await self.uow.employees.get_analytics(data)

        if len(rows) == 0: return EmployeeAnalyticsResponse(items = [])

        return EmployeeAnalyticsResponse(
            items = [
                EmployeeAnalyticsBaseResponse(
                    employee_id = row.employee_id,
                    employee_fullname = row.fullname,
                    appointments = row.appointments_amount,
                    services = row.services_amount,
                    revenue = row.services_final_price_sum
                )
                for row in rows
            ]
        )
        