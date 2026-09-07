from fastapi import APIRouter, Body, Depends, Request, Response
from src.core.dependencies.auth import get_current_staff
from src.core.dependencies.uow import make_service_dependency
from src.schemas.auth.login import LoginResponseSchema, LoginSchema
from src.schemas.auth.response import MeResponseSchema
from src.schemas.staff.request import StaffUpdatePasswordSchema
from src.services.auth.auth_service import AuthService

router = APIRouter()

get_auth_service = make_service_dependency(AuthService)

@router.post(
    "/login",
    status_code = 200,
    response_model = LoginResponseSchema,
    summary = "Вход в систему",
    description = "Проверяет логин и пароль сотрудника и, в случае успеха, возвращает Cookie с access_token, refresh_token и информацию о пользователе. Организация должна быть активна.")
async def login(data: LoginSchema, request: Request, response: Response,
                authService: AuthService = Depends(get_auth_service)):
    return await authService.login(data, request, response)

@router.post(
    "/refresh",
    status_code = 204,
    summary = "Обновить токены доступа",
    description = "Выпускает новую пару access_token / refresh_token на основе действующего refresh_token из Cookie."
)
async def refresh_tokens(
    request: Request,
    response: Response,
    authService: AuthService = Depends(get_auth_service)
):
    return await authService.refresh(request, response)

@router.post(
    "/logout",
    status_code = 204,
    summary = "Выход из системы",
    description = "Удаляет Cookie access_token и refresh_token и очищает закэшированные разрешения сотрудника."
)
async def logout_user(
    response: Response,
    authService: AuthService = Depends(get_auth_service),
    current_staff: dict = Depends(get_current_staff)
):
    return await authService.logout(response)

@router.post(
    "/change-password",
    status_code = 204,
    summary = "Сменить пароль",
    description = "Меняет собственный пароль сотрудника. Администратор может сменить пароль другого сотрудника, указав его `id`; в этом случае вместо `oldPassword` проверяется текущий пароль администратора."
)
async def change_password(
        data: StaffUpdatePasswordSchema = Body(...),
        authService: AuthService = Depends(get_auth_service),
        current_staff: dict = Depends(get_current_staff)):
    return await authService.change_password(data = data)

@router.patch(
    "/reset-password",
    status_code = 200,
    response_model = str,
    summary = "Сбросить пароль сотрудника",
    description = "Генерирует новый случайный пароль для сотрудника с указанным `id` и возвращает его в открытом виде (единственный раз, сохранить не получится повторно)."
)
async def reset_password(
        id: int,
        authService: AuthService = Depends(get_auth_service),
        current_staff: dict = Depends(get_current_staff)):
    return await authService.reset_password(id)

@router.get(
    "/me",
    status_code = 200,
    response_model = MeResponseSchema,
    summary = "Текущий пользователь",
    description = "Возвращает данные сотрудника, авторизованного в текущей сессии (по access_token из Cookie)."
)
async def get_me(authService: AuthService = Depends(get_auth_service),
                current_staff: dict = Depends(get_current_staff)):
    return await authService.get_me()