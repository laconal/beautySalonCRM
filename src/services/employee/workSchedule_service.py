from datetime import date
import math
from src.core.decorators.requireID import require_exists
from src.core.dependencies.uow import UnitOfWork
from src.exceptions.workSchedule_exceptions import WorkScheduleNotFound
from src.repository.employee.employee_model import Employee
from src.repository.employee.workSchedule_model import WorkSchedule
from src.schemas.base import RequestAllObject
from src.schemas.work_schedule.create import WorkScheduleCreateSchema
from src.schemas.work_schedule.response import WorkScheduleBaseResponseSchema, WorkScheduleResponseSchema
from src.schemas.work_schedule.update import WorkScheduleUpdateSchema

class WorkScheduleService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def _to_response_schedule(schedule: WorkSchedule) -> WorkScheduleBaseResponseSchema:
        return WorkScheduleBaseResponseSchema(
            id = schedule.id,
            created_at = schedule.created_at,
            updated_at = schedule.updated_at,
            created_by = schedule.created_by,
            archived = schedule.archived,
            day = schedule.day_of_week,
            start_time = schedule.start_time,
            end_time = schedule.end_time
        )

    @require_exists("employees", target_param = "employee_id")
    async def create(self, data: WorkScheduleCreateSchema) -> WorkScheduleResponseSchema:
        createdSchedules = [
            await self.uow.work_schedules.create(
                WorkSchedule(
                    employee_id = data.employee_id,
                    day_of_week = schedule.day,
                    start_time = schedule.start_time,
                    end_time = schedule.end_time
                )
            )
            for schedule in data.work_schedules
        ]

        return WorkScheduleResponseSchema(
            employee_id = data.employee_id,
            work_schedules = [self._to_response_schedule(schedule) for schedule in createdSchedules]
        )

    async def update(self, data: WorkScheduleUpdateSchema) -> WorkScheduleResponseSchema:
        updatedSchedules = []
        for schedule in data.work_schedules:
            scheduleExists = await self.uow.work_schedules.get(schedule.id)
            if scheduleExists is None: raise WorkScheduleNotFound(schedule.id)
            
            updated = await self.uow.work_schedules.update(
                schedule.id,
                start_time = schedule.start_time,
                end_time = schedule.end_time
            )
            updatedSchedules.append(updated)

        return WorkScheduleResponseSchema(
            employee_id = updatedSchedules[0].employee_id,
            work_schedules = [self._to_response_schedule(schedule) for schedule in updatedSchedules]
        )

    async def get(self, id: int) -> WorkScheduleResponseSchema:
        result = await self.uow.work_schedules.get(id)
        if result is None: raise WorkScheduleNotFound(id)
        return WorkScheduleResponseSchema(
            employee_id = result.employee_id,
            work_schedules = [self._to_response_schedule(result)]
        )

    async def get_many(self, ids: list[int]) -> list[WorkSchedule]:
        results = await self.uow.work_schedules.get_by_ids(ids)
        for result in results:
            result.days = [result.day_of_week]
        return results

    async def get_all(self, data: RequestAllObject) -> dict:
        items, total_items = await self.uow.work_schedules.get_all(data)
        responseItems = [
            WorkScheduleResponseSchema(
                employee_id = item.employee_id,
                work_schedules = [self._to_response_schedule(item)]
            )
            for item in items
        ]

        total_pages = math.ceil(total_items / data.pageSize) if data.pageSize > 0 else 0

        return {
            "items": responseItems,
            "page": data.page,
            "pageSize": data.pageSize,
            "totalItems": total_items,
            "totalPages": total_pages
        }
    
    async def delete(self, id: int) -> bool:
        result = await self.uow.work_schedules.delete(id)
        if result is None: raise WorkScheduleNotFound(id)
        return result
    
    async def getEmployeesByDate(self, day: date) -> list[Employee]:
        employees = await self.uow.work_schedules.get_employees_by_date(day)
        result = [employee for employee in employees if len(employee.services) >= 1]
        return result