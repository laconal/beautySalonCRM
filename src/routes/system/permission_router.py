from fastapi import APIRouter, Depends
from src.core.dependencies.permissions import require_admin
from src.core.permissions import PERMISSIONS
from src.exceptions.auth_exceptions import PermissionNotFound
from src.schemas.permission.response import PermissionResponseSchema

router = APIRouter(dependencies = [Depends(require_admin)])

@router.get(
    "",
    response_model = list[PermissionResponseSchema],
    status_code = 200,
    summary = "Список доступных кодов разрешений",
    description = "Возвращает справочник всех кодов разрешений, доступных в системе, с их названием и относящимся к ним ресурсом. Используется для построения форм назначения ролей и прямых разрешений."
)
async def get_all() -> list[PermissionResponseSchema]:
    return [
        PermissionResponseSchema(code = code, resource = meta["resource"], name = meta["name"])
        for code, meta in PERMISSIONS.items()
    ]

@router.get(
    "/{code}",
    response_model = PermissionResponseSchema,
    status_code = 200,
)
async def get(code: int):
    if code not in PERMISSIONS: raise PermissionNotFound(code)
    item = PERMISSIONS.get(code)
    return PermissionResponseSchema(code = code, resource = item["resource"], name = item["name"])