from typing import Literal

from fastapi import APIRouter, Depends, status

from src.core.dependencies.permissions import require_parent_tenant, require_permission
from src.core.dependencies.uow import make_service_dependency
from src.core.permissions import PermissionCode
from src.schemas.tenant.create import BranchAdminCreateSchema, TenantBranchCreateSchema
from src.schemas.tenant.response import (
    BranchAdminResponseSchema,
    BranchCreateAdminResponse,
    TenantBranchCreateResponseSchema,
    TenantBranchReportItemSchema,
    TenantBranchReportSchema,
    TenantBranchResponseSchema,
)
from src.schemas.tenant.update import UpdateBranchAdminPassword, UpdateBranchAdminSchema, UpdateBranchSchema
from src.services.system.tenantBranches_service import TenantBranchesService

router = APIRouter()

get_tenant_branches_service = make_service_dependency(TenantBranchesService)

@router.post(
    "",
    response_model = TenantBranchCreateResponseSchema,
    status_code = status.HTTP_201_CREATED,
    summary = "Создать филиал",
    description = "Создает новый филиал (дочернюю организацию) и его администратора. Доступно только головной организации — у филиала создавать свои филиалы нельзя.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_CREATE]))
    ]
)
async def create(data: TenantBranchCreateSchema,
                 tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.create(data)

@router.post(
    "/create-branch-admin",
    response_model = BranchCreateAdminResponse,
    status_code = 201,
    summary = "Создать админа для филиала",
    description = "Создает нового админа для филиала (дочернюю организацию). Доступно только головной организации — у филиала создавать свои филиалы нельзя.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_CREATE_ADMIN]))
    ]
)
async def create_branch_admin(data: BranchAdminCreateSchema,
                 tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.create_branch_admin(data)

@router.get(
    "",
    response_model = list[TenantBranchResponseSchema],
    status_code = status.HTTP_200_OK,
    summary = "Список филиалов",
    description = "Возвращает список филиалов текущей организации.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_READ]))
    ]
)
async def get_all(tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.get_all()

@router.post(
    "/reset-admin-password",
    status_code = 200,
    summary = "Сбрасывает / обновляет пароль админа из выбранного филиала",
    description = """Сбрасывает или обновляет пароль админа.
    Указывается `branch_id` (id филиала), `admin_id` (id админа).
    Поле `password` опционален, если не указывается - новый пароль генерируется случайным образом и в ответе возвращает сгенерированный пароль.
    В указанном `password` возвращает пустой ответ
    """,
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_RESET_ADMIN_PASSWORD]))
    ]
)
async def reset_admin_password(
    data: UpdateBranchAdminPassword,
    tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.reset_admin_password(data)

@router.get(
    "/report",
    response_model = TenantBranchReportSchema,
    status_code = status.HTTP_200_OK,
    summary = "Отчёт по филиалам",
    description = "Возвращает агрегированный отчёт (кол-во сотрудников/сотрудников-исполнителей/"
        "клиентов/записей/услуг/материалов и сумма доходов/расходов) по каждому филиалу и по всей "
        "организации в целом. Доступно только головной организации.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_GET_REPORT]))
    ]
)
async def get_report(tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.get_report()

@router.get(
    "/report/{id}",
    response_model = TenantBranchReportItemSchema,
    status_code = status.HTTP_200_OK,
    summary = "Отчёт по конкретному филиалу",
    description = "Возвращает агрегированный отчёт по одному филиалу. Доступно только головной "
        "организации, и только для её собственных филиалов.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_GET_REPORT]))
    ]
)
async def get_branch_report(id: int, tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.get_branch_report(id)

@router.patch(
    "/update-admin",
    response_model = BranchAdminResponseSchema,
    status_code = status.HTTP_200_OK,
    summary = "Изменить статус/роль админа филиала",
    description = "Изменяет `active` и/или `staff_type` админа выбранного филиала. Указывается "
        "`branch_id` (id филиала) и `admin_id` (id админа), хотя бы одно из полей `active`/`staff_type` "
        "обязательно. Доступно только головной организации.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_UPDATE_ADMIN]))
    ]
)
async def update_branch_admin(
    data: UpdateBranchAdminSchema,
    tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.update_branch_admin(data)

@router.patch(
    "/update",
    response_model = TenantBranchResponseSchema,
    status_code = status.HTTP_200_OK,
    summary = "Изменить данные филиала",
    description = "Изменяет `name`, `TIN` и/или `active` выбранного филиала. Указывается `branch_id` "
        "(id филиала), хотя бы одно из полей `name`/`TIN`/`active` обязательно. При смене `name` "
        "проверяется, что оно не занято другой организацией. Доступно только головной организации.",
    dependencies = [
        Depends(require_parent_tenant),
        Depends(require_permission([PermissionCode.TENANT_BRANCH_UPDATE_ADMIN]))
    ]
)
async def update_branch(
    data: UpdateBranchSchema,
    tenantBranchesService: TenantBranchesService = Depends(get_tenant_branches_service)):
    return await tenantBranchesService.update_branch(data)