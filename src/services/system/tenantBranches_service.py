import secrets
import string

from src.core.auth.security import generate_password, hash_password
from src.core.cache.permission_cache import delete_staff_permissions
from src.core.cache.tenant_cache import delete_tenant_active
from src.core.dependencies.context import cleared_actor_context, get_current_actor_id, get_current_tenant_id
from src.core.dependencies.uow import UnitOfWork
from src.core.utils.common import get_current_tenant_or_raise
from src.database.base import Actor, ActorType
from src.database.session import SessionLocal
from src.exceptions.staff_exceptions import StaffLoginDuplicate, StaffNotFound, StaffTenantConflict
from src.exceptions.tenant_exceptions import BranchDoesNotBelongToTenant, TenantNameTaken, TenantNotFound
from src.repository.appointment.appointment_model import Appointment
from src.repository.client.client_model import Client
from src.repository.employee.employee_model import Employee
from src.repository.material.material_model import Material
from src.repository.service.service_model import Service
from src.repository.staff.staff_model import Staff, StaffType
from src.repository.tenant.tenant_model import Tenant
from src.repository.transaction.transaction_model import Transaction, TransactionType
from src.schemas.tenant.create import BranchAdminCreateSchema, TenantBranchCreateSchema
from src.schemas.tenant.response import (
    BranchAdminResponseSchema,
    BranchCreateAdminResponse,
    TenantBranchReportItemSchema,
    TenantBranchReportSchema,
    TenantBranchReportTotalsSchema,
)
from src.schemas.tenant.update import UpdateBranchAdminPassword, UpdateBranchAdminSchema, UpdateBranchSchema
from src.services.system.tenant_service import provision_tenant
from sqlalchemy import func, select, update

REPORT_COUNT_FIELDS: list[tuple[str, type]] = [
    ("staffs", Staff),
    ("employees", Employee),
    ("clients", Client),
    ("appointments", Appointment),
    ("services", Service),
    ("materials", Material),
]

class TenantBranchesService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, data: TenantBranchCreateSchema) -> dict:
        tenant = await get_current_tenant_or_raise(self.uow)
        creator_actor_id = get_current_actor_id()
        duplicateCheck = await self.uow.tenants.get(name = data.company_name)
        if duplicateCheck is not None: raise TenantNameTaken(data.company_name)

        # provision_tenant writes rows tagged with the new branch's tenant_id, which the
        # request's tenant-scoped session (self.uow.db) would reject as cross-tenant data
        # injection (src/core/dependencies/tenantFilter.py). Use a standalone session
        # without that filter attached, same as sqladmin's TenantCreateView does.

        async with SessionLocal() as session:
            with cleared_actor_context():
                result = await provision_tenant(
                    session,
                    company_name = data.company_name,
                    company_tin = data.company_tin,
                    admin_login = data.admin_login,
                    admin_firstname = data.admin_firstname,
                    admin_password = data.admin_password,
                    parent_id = tenant.id,
                    created_by_actor_id = creator_actor_id,
                )
                await session.commit()
        return result

    async def get_all(self) -> list[Tenant]:
        tenant = await get_current_tenant_or_raise(self.uow)
        return await self.uow.tenants.get_branches(tenant.id)

    async def _compute_tenant_counts(self, tenant_ids: list[int]) -> dict[int, dict[str, int]]:
        counts: dict[int, dict[str, int]] = {
            tid: {"staffs": 0, "employees": 0, "clients": 0, "appointments": 0,
                  "services": 0, "materials": 0, "income": 0, "expense": 0}
            for tid in tenant_ids
        }
        if not tenant_ids:
            return counts

        # these read across tenants the caller doesn't own, which the request's
        # tenant-scoped session would otherwise filter down to just its own rows.
        for field_name, model in REPORT_COUNT_FIELDS:
            result = await self.uow.db.execute(
                select(model.tenant_id, func.count())
                .where(model.tenant_id.in_(tenant_ids), model.archived.is_(False))
                .group_by(model.tenant_id)
                .execution_options(skip_tenant_filter = True)
            )
            for tenant_id, count in result.all():
                counts[tenant_id][field_name] = count

        transactions_result = await self.uow.db.execute(
            select(
                Transaction.tenant_id,
                Transaction.type,
                func.coalesce(func.sum(Transaction.amount), 0),
            )
            .where(
                Transaction.tenant_id.in_(tenant_ids),
                Transaction.archived.is_(False),
                Transaction.cancelled.is_(False),
            )
            .group_by(Transaction.tenant_id, Transaction.type)
            .execution_options(skip_tenant_filter = True)
        )
        for tenant_id, tx_type, total in transactions_result.all():
            if tx_type == TransactionType.INCOME:
                counts[tenant_id]["income"] = total
            elif tx_type == TransactionType.EXPENSE:
                counts[tenant_id]["expense"] = total

        return counts

    async def get_report(self) -> TenantBranchReportSchema:
        tenant = await get_current_tenant_or_raise(self.uow)
        branches = await self.uow.tenants.get_branches(tenant.id)

        tenant_ids = [branch.id for branch in branches]
        tenant_names = {branch.id: branch.name for branch in branches}

        counts = await self._compute_tenant_counts(tenant_ids)

        branches_report = [
            TenantBranchReportItemSchema(
                tenant_id = tid,
                tenant_name = tenant_names[tid],
                **counts[tid],
            )
            for tid in tenant_ids
        ]

        total = TenantBranchReportTotalsSchema(
            staffs = sum(c["staffs"] for c in counts.values()),
            employees = sum(c["employees"] for c in counts.values()),
            clients = sum(c["clients"] for c in counts.values()),
            appointments = sum(c["appointments"] for c in counts.values()),
            services = sum(c["services"] for c in counts.values()),
            materials = sum(c["materials"] for c in counts.values()),
            income = sum(c["income"] for c in counts.values()),
            expense = sum(c["expense"] for c in counts.values()),
        )

        return TenantBranchReportSchema(branches = branches_report, total = total)

    async def get_branch_report(self, branch_id: int) -> TenantBranchReportItemSchema:
        parentTenant = await get_current_tenant_or_raise(self.uow)
        branch = await self.uow.tenants.get(id = branch_id)
        if branch is None: raise TenantNotFound(branch_id)
        if branch.parent_id != parentTenant.id: raise BranchDoesNotBelongToTenant(parentTenant.id, branch_id)

        counts = await self._compute_tenant_counts([branch_id])

        return TenantBranchReportItemSchema(
            tenant_id = branch_id,
            tenant_name = branch.name,
            **counts[branch_id],
        )

    async def create_branch_admin(self, data: BranchAdminCreateSchema) -> BranchCreateAdminResponse:
        parentTenant = await get_current_tenant_or_raise(self.uow)
        tenant = await self.uow.tenants.get(id = data.branch_id)
        if tenant is None: raise TenantNotFound(data.branch_id)
        if tenant.parent_id != parentTenant.id: raise BranchDoesNotBelongToTenant(parentTenant.id, data.branch_id)

        async with SessionLocal() as session:
            with cleared_actor_context():
                stmt = (
                    select(Staff)
                    .where(Staff.login == data.admin_login)
                )
                result = await session.execute(stmt)
                login = result.scalar_one_or_none()
                if login is not None: raise StaffLoginDuplicate()

                actor = Actor(tenant_id = data.branch_id, actor_type = ActorType.STAFF, name = data.admin_firstname)
                session.add(actor)
                await session.flush()

                passwordData = generate_password(data.admin_password)
                plainPassword = data.admin_password if data.admin_password is not None else passwordData["plain"]

                admin_user = Staff(
                    tenant_id = data.branch_id,
                    login = data.admin_login,
                    firstname = data.admin_firstname,
                    staff_type = StaffType.ADMIN,
                    hashed_password = passwordData["hashed"],
                    actor_id = actor.id
                )
                session.add(admin_user)

                # build+validate the response shape before committing, so a mismatch
                # fails (and rolls back) instead of persisting and then 500ing on the way out
                response = BranchCreateAdminResponse(login = admin_user.login, password = plainPassword)

                await session.commit()
        return response
         
    async def reset_admin_password(self, data: UpdateBranchAdminPassword) -> str | None:
        """
        Resets / update admin's password\n
        If provided `password` - set hashed password and return None\n
        If `password` has not provided - generate random password, set hashed and return
        """
        parentTenant = await get_current_tenant_or_raise(self.uow)
        tenant = await self.uow.tenants.get(id = data.branch_id)
        if tenant is None: raise TenantNotFound(data.branch_id)
        if tenant.parent_id != parentTenant.id: raise BranchDoesNotBelongToTenant(parentTenant.id, data.branch_id)

        result = await self.uow.db.execute(
            select(Staff)
            .where(Staff.id == data.admin_id)
            .execution_options(skip_tenant_filter = True)
        )
        admin = result.scalar_one_or_none()
        if admin is None: raise StaffNotFound()
        if admin.tenant_id != tenant.id: raise StaffTenantConflict(data.admin_id, data.branch_id)

        plainPassword: str
        if data.password is not None: plainPassword = data.password
        else:
            alphabet = (
                string.ascii_letters +
                string.digits +
                "!@#$%^&*-_=+?"
            )

            plainPassword = "".join(secrets.choice(alphabet) for _ in range(16))
        hashed = hash_password(plainPassword)

        async with SessionLocal() as session:
            await session.execute(
                update(Staff)
                .where(Staff.id == data.admin_id)
                .values(hashed_password = hashed)
            )
            await session.commit()

        return plainPassword if data.password is None else None

    async def update_branch_admin(self, data: UpdateBranchAdminSchema) -> BranchAdminResponseSchema:
        parentTenant = await get_current_tenant_or_raise(self.uow)
        tenant = await self.uow.tenants.get(id = data.branch_id)
        if tenant is None: raise TenantNotFound(data.branch_id)
        if tenant.parent_id != parentTenant.id: raise BranchDoesNotBelongToTenant(parentTenant.id, data.branch_id)

        result = await self.uow.db.execute(
            select(Staff)
            .where(Staff.id == data.admin_id)
            .execution_options(skip_tenant_filter = True)
        )
        admin = result.scalar_one_or_none()
        if admin is None: raise StaffNotFound()
        if admin.tenant_id != tenant.id: raise StaffTenantConflict(data.admin_id, data.branch_id)

        updateFields = data.model_dump(exclude = {"branch_id", "admin_id"}, exclude_unset = True)

        async with SessionLocal() as session:
            await session.execute(
                update(Staff)
                .where(Staff.id == data.admin_id)
                .values(**updateFields)
            )
            await session.commit()

        # staff_type/active are cached alongside permissions (src/core/cache/permission_cache.py)
        # with a TTL tied to the refresh token lifetime - without this, a demoted/deactivated
        # admin would keep their old elevated access until the cache entry naturally expires.
        await delete_staff_permissions(data.admin_id)

        refreshed = await self.uow.db.execute(
            select(Staff)
            .where(Staff.id == data.admin_id)
            .execution_options(skip_tenant_filter = True)
        )
        updatedAdmin = refreshed.scalar_one_or_none()

        return BranchAdminResponseSchema.model_validate(updatedAdmin)

    async def update_branch(self, data: UpdateBranchSchema) -> Tenant:
        parentTenant = await get_current_tenant_or_raise(self.uow)
        tenant = await self.uow.tenants.get(id = data.branch_id)
        if tenant is None: raise TenantNotFound(data.branch_id)
        if tenant.parent_id != parentTenant.id: raise BranchDoesNotBelongToTenant(parentTenant.id, data.branch_id)

        updateFields = data.model_dump(exclude = {"branch_id"}, exclude_unset = True)

        if "name" in updateFields:
            existing = await self.uow.tenants.get(name = updateFields["name"])
            if existing is not None and existing.id != tenant.id:
                raise TenantNameTaken(updateFields["name"])

        # Tenant isn't TenantMixin (no tenant_id column), so this write doesn't hit the
        # cross-tenant before_flush guard the way Staff/TenantIntegration updates do -
        # no need for a standalone session here.
        updated = await self.uow.tenants.update(tenant.id, **updateFields)
        if updated is None: raise TenantNotFound(data.branch_id)

        if "active" in updateFields:
            # active status is cached (src/core/cache/tenant_cache.py) with a TTL tied to the
            # refresh token lifetime - without this, a deactivated branch would keep serving
            # its already-authenticated staff until the cache entry naturally expires.
            await delete_tenant_active(tenant.id)

        return updated