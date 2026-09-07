import string
from fastapi import Request, Response
from src.core.cache.permission_cache import delete_staff_permissions, set_staff_permissions
from src.core.config import settings
from src.core.cache.login_attempts_cache import (
    account_blocked_until,
    ip_blocked_until,
    is_account_blocked,
    is_ip_blocked,
    register_failed_account_login,
    register_failed_ip_login,
    reset_failed_account_login,
    reset_failed_ip_login,
)
from src.core.dependencies.auth import is_tenant_active
from src.core.dependencies.context import get_current_staff_id
from src.core.dependencies.uow import UnitOfWork
from src.core.permissions import compute_effective_permissions
from src.core.utils.common import get_client_ip
from src.exceptions.auth_exceptions import AccountTemporarilyLocked, AdminPreviligesRequired, IncorrectCredentials, IncorrectOldPassword, RefreshTokenMissing, TenantIsInactive, TokenIsInvalid, TooManyLoginAttempts
from src.exceptions.employee_exceptions import EmployeeNotFound
from src.exceptions.staff_exceptions import StaffIsInactive, StaffNotFound
from src.repository.employee.employee_model import Employee
from src.repository.staff.staff_model import Staff, StaffType
from src.schemas.auth.login import LoginResponseSchema, LoginSchema
from src.core.auth.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.schemas.auth.response import MeResponseSchema
from src.schemas.base import ActorResponseSchema
from src.schemas.employee.response import EmployeeResponseBase
import secrets

from src.schemas.staff.request import StaffUpdatePasswordSchema

class AuthService():
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def login(self, data: LoginSchema, request: Request, response: Response) -> LoginResponseSchema:
        ip = get_client_ip(request)

        if await is_ip_blocked(ip):
            raise TooManyLoginAttempts(await ip_blocked_until(ip))

        if await is_account_blocked(data.login):
            raise AccountTemporarilyLocked(await account_blocked_until(data.login))

        staff = await self.uow.staffs.get(login = data.login)

        if staff is None or not verify_password(staff.hashed_password, data.password):
            await register_failed_ip_login(ip)
            await register_failed_account_login(data.login)
            raise IncorrectCredentials()

        await reset_failed_ip_login(ip)
        await reset_failed_account_login(data.login)

        if not staff.active: raise StaffIsInactive()
        
        if not await is_tenant_active(staff.tenant_id): raise TenantIsInactive()

        employee: Employee | None = None
        if staff.employee_id:
            employee = await self.uow.employees.get(staff.employee_id)
            if employee is None: raise EmployeeNotFound(staff.employee_id)

        accessTokenPayload = {
            "sub": staff.login,
            "id": staff.id,
            "tenant_id": staff.tenant_id,
            "actor_id": staff.actor_id,
            "type": "access"
        }
        refreshTokenPayload = accessTokenPayload.copy()
        refreshTokenPayload["type"] = "refresh"

        accessToken = create_access_token(accessTokenPayload)
        refreshToken = create_refresh_token(refreshTokenPayload)

        response.set_cookie(
            key = "access_token",
            value = accessToken,
            httponly = True,
            secure = True,
            samesite = "lax"
        )

        response.set_cookie(
            key = "refresh_token",
            value = refreshToken,
            httponly = True,
            secure = True,
            samesite = "lax"
        )

        await set_staff_permissions(
            staff.id,
            staff.staff_type,
            staff.active,
            compute_effective_permissions(staff),
            ttl = settings.ACCESS_TOKEN_EXPIRE_SECONDS
        )

        tenant = await self.uow.tenants.get(id = staff.tenant_id)
        return LoginResponseSchema(
            id = staff.id,
            tenant_id = staff.tenant_id,
            created_at = staff.created_at,
            updated_at = staff.updated_at,
            creator = ActorResponseSchema.model_validate(staff.actor) if staff.actor else None,
            archived = staff.archived,
            login=staff.login,
            permissions = staff.permissions,
            roles = staff.roles,
            employee=EmployeeResponseBase.model_validate(employee) if employee else None,
            firstname=staff.firstname,
            lastname=staff.lastname,
            middlename=staff.middlename,
            active=staff.active,
            staff_type=staff.staff_type,
            tenant_name = tenant.name
        )

    async def refresh(self, request: Request, response: Response):
        refreshToken = request.cookies.get("refresh_token")
        if not refreshToken: raise RefreshTokenMissing()

        payload = decode_token(refreshToken) 
        if payload is None: raise TokenIsInvalid()
        
        if payload.get("type") != "refresh": raise TokenIsInvalid()

        login = payload.get("sub")
        if login is None: raise TokenIsInvalid()

        user = await self.uow.staffs.get(login = login)
        if not user: raise StaffNotFound()
        if not user.active: raise StaffIsInactive()

        if not await is_tenant_active(user.tenant_id): raise TenantIsInactive()

        accessTokenPayload = {
            "sub": user.login,
            "id": user.id,
            "tenant_id": user.tenant_id,
            "actor_id": user.actor_id,
            "type": "access"
        }
        refreshTokenPayload = accessTokenPayload.copy()
        refreshTokenPayload["type"] = "refresh"

        accessToken = create_access_token(accessTokenPayload)
        refreshToken = create_refresh_token(refreshTokenPayload)

        response.set_cookie(
            key="access_token", 
            value=accessToken, 
            httponly=True, 
            secure=True, 
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=refreshToken,
            httponly=True,
            secure=True,
            samesite="lax"
        )

        await set_staff_permissions(
            user.id,
            user.staff_type,
            user.active,
            compute_effective_permissions(user),
            ttl = settings.ACCESS_TOKEN_EXPIRE_SECONDS
        )

    async def logout(self, response: Response):
        staff_id = get_current_staff_id()
        response.delete_cookie(
            key="access_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )
        await delete_staff_permissions(staff_id)

    async def change_password(self, data: StaffUpdatePasswordSchema):
        selfUser = get_current_staff_id()
        targetID = data.id if data.id is not None else selfUser

        user = await self.uow.staffs.get(id = targetID)
        if user is None: raise StaffNotFound()

        if targetID != selfUser:
            actor = await self.uow.staffs.get(id = selfUser)
            if actor is None or actor.staff_type != StaffType.ADMIN: raise AdminPreviligesRequired()

            hashed = hash_password(data.newPassword)
            await self.uow.staffs.update(user.id, hashed_password = hashed)   
        else:
            verify = verify_password(user.hashed_password, data.oldPassword)
            if not verify: raise IncorrectOldPassword()

            hashed = hash_password(data.newPassword)
            await self.uow.staffs.update(user.id, hashed_password = hashed)
    
    async def reset_password(self, id: int) -> str:
        user = await self.uow.staffs.get(id = id)
        if user is None: raise StaffNotFound()

        alphabet = (
            string.ascii_letters +
            string.digits +
            "!@#$%^&*-_=+?"
        )

        newPassword = "".join(secrets.choice(alphabet) for _ in range(16))

        hashed = hash_password(newPassword)
        await self.uow.staffs.update(id, hashed_password = hashed)
        return newPassword
    
    async def get_me(self) -> MeResponseSchema:
        staff_id = get_current_staff_id()
        staff = await self.uow.staffs.get(id = staff_id)
        if staff is None: raise StaffNotFound()

        employee: Employee | None = None
        if staff.employee_id:
            employee = await self.uow.employees.get(staff.employee_id)

        return MeResponseSchema(
            id = staff.id,
            tenant_id = staff.tenant_id,
            created_at = staff.created_at,
            updated_at = staff.updated_at,
            creator = ActorResponseSchema.model_validate(staff.actor) if staff.actor else None,
            archived = staff.archived,
            login=staff.login,
            permissions = staff.permissions,
            roles = staff.roles,
            employee=EmployeeResponseBase.model_validate(employee) if employee else None,
            firstname=staff.firstname,
            lastname=staff.lastname,
            middlename=staff.middlename,
            active=staff.active,
            staff_type=staff.staff_type
        )