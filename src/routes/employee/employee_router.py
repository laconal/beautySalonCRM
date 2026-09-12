from fastapi import APIRouter, Depends, Query, status
from src.core.dependencies.permissions import require_permission
from src.core.dependencies.uow import make_service_dependency
from src.core.permissions import PermissionCode
from src.schemas.appointment.response import AppointmentResponseSchema
from src.schemas.base import PaginatedResponseSchema, PaginationSchema, RequestAllObject
from src.schemas.employee.create import EmployeeCreateSchema
from src.schemas.employee.response import EmployeeResponseBase, EmployeeWorkScheduleResponse
from src.schemas.employee.update import EmployeeUpdateSchema
from src.schemas.payroll.response import PayrollResponseSchema
from src.services.employee.employee_service import EmployeeService

router = APIRouter()

get_employee_service = make_service_dependency(EmployeeService)

@router.post(
    "",
    response_model=EmployeeResponseBase,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового сотрудника с привязанными услугами",
    description="Создает сотрудника и, при необходимости, сразу привязывает к нему специализацию (`specialization_id`) и список услуг, которые он оказывает (`services_ids`). Возраст сотрудника должен быть не менее 18 лет.",
    dependencies=[Depends(require_permission([PermissionCode.EMPLOYEE_CREATE]))]
)
async def create(
    data: EmployeeCreateSchema,
    employeeService: EmployeeService = Depends(get_employee_service)
):
    return await employeeService.create(data)

@router.post(
    "/get-all",
    response_model=PaginatedResponseSchema[EmployeeResponseBase],
    status_code=status.HTTP_200_OK,
    summary="Получить всех сотрудников",
    description="Возвращает постраничный список сотрудников организации с поддержкой фильтрации.",
    dependencies=[Depends(require_permission([PermissionCode.EMPLOYEE_READ]))]
)
async def get_all(params: RequestAllObject,
    employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.get_all(params)

@router.get(
    "/export",
    status_code = 200,
    summary = "Экспорт списка сотрудников, в формате Excel или JSON",
    dependencies = [Depends(require_permission([PermissionCode.EMPLOYEE_EXPORT]))])
async def export_employees(
    format: str = Query("json", pattern="^(json|xlsx)$"),
    employeeService: EmployeeService = Depends(get_employee_service),
):
    return await employeeService.export(format)

@router.get(
    "/{id}",
    response_model = EmployeeResponseBase,
    status_code = status.HTTP_200_OK,
    summary="Получить сотрудника по ID",
    dependencies=[Depends(require_permission([PermissionCode.EMPLOYEE_READ]))]
)
async def get(id: int,
    employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.get(id)

@router.patch(
    "",
    response_model=EmployeeResponseBase,
    status_code=status.HTTP_200_OK,
    summary="Обновить сотрудника",
    description="Обновляет данные сотрудника по его `id`, включая привязанные услуги (`services`) и специализацию. Передаются только изменяемые поля.",
    dependencies=[Depends(require_permission([PermissionCode.EMPLOYEE_UPDATE]))]
)
async def update(data: EmployeeUpdateSchema,
    employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.update(data)

@router.get(
    "/{id}/work-schedules",
    status_code = status.HTTP_200_OK,
    response_model = EmployeeWorkScheduleResponse,
    summary = "График работы сотрудника",
    description = "Возвращает график работы и отсутствия сотрудника",
    dependencies=[Depends(require_permission([PermissionCode.EMPLOYEE_READ]))]
)
async def get_workSchedules(id: int,
    employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.get_workSchedules(id)

@router.get(
    "/{id}/payrolls",
    status_code = status.HTTP_200_OK,
    response_model = PaginatedResponseSchema[PayrollResponseSchema],
    summary = "Начисления сотрудника",
    description = "Возвращает постраничный список начислений (зарплата, премии, штрафы, комиссии) сотрудника.",
    dependencies=[Depends(require_permission([PermissionCode.PAYROLL_READ]))]
)
async def get_payrolls(id: int,
                       params: PaginationSchema = Depends(),
                       employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.get_payrolls(params, id)

@router.get(
    "/{id}/appointments",
    status_code = status.HTTP_200_OK,
    response_model=PaginatedResponseSchema[AppointmentResponseSchema],
    summary = "Посещения сотрудника",
    description = "Возвращает постраничный список посещений, в которых участвует данный сотрудник.",
    dependencies=[Depends(require_permission([PermissionCode.APPOINTMENT_READ]))]
)
async def get_appointments(id: int,
                           params: PaginationSchema = Depends(),
                           employeeService: EmployeeService = Depends(get_employee_service)):
    return await employeeService.get_appointments(params, id)