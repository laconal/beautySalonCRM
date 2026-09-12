from datetime import date
from pydantic import  BaseModel, ConfigDict, Field
from src.schemas.base import BaseResponseSchema
from src.schemas.service.response import ServiceResponseSchema
from src.schemas.work_schedule.response import AbsenceResponseSchema, WorkScheduleBaseResponseSchema

class EmployeeResponseBase(BaseResponseSchema):
    firstname: str = Field(..., max_length=100, description="Employee's first name")
    lastname: str | None = Field(None, max_length=100)
    middlename: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    birth_date: date
    active: bool = True
    specialization_id: int | None = None
    services: list[ServiceResponseSchema]
    salary_fixed: int = 0
    percent_from_services: int = 0
    percent_from_sales: int = 0
    notes: str | None = None
    
    model_config = ConfigDict(from_attributes=True)

class EmployeeWorkScheduleResponse(BaseModel):
    work_schedules: list[WorkScheduleBaseResponseSchema]
    absences: list[AbsenceResponseSchema]

    class ConfigDict: from_attributes = True