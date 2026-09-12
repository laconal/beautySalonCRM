import secrets
import string
from src.core.auth.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.base import Actor, ActorType
from src.repository import Tenant, TenantIntegration, Staff
from src.schemas.tenant.base import TenantPreferencesSchema

async def provision_tenant(db: AsyncSession,
                           company_name: str,
                           admin_login: str,
                           admin_firstname: str,
                           admin_password: str | None = None,
                           company_tin: str | None = None,
                           parent_id: int | None = None,
                           created_by_actor_id: int | None = None, ) -> Tenant:
    
    defaultPreferences = TenantPreferencesSchema().model_dump()
    tenant = Tenant(
        name=company_name,
        TIN=company_tin,
        preferences = defaultPreferences,
        parent_id = parent_id,
        created_by_actor_id = created_by_actor_id,
    )
    db.add(tenant)
    await db.flush()

    integrations = TenantIntegration(tenant_id=tenant.id)
    db.add(integrations)

    actor = Actor(tenant_id=tenant.id, actor_type=ActorType.STAFF, name=admin_firstname)
    db.add(actor)
    await db.flush()

    newPassword: str
    if admin_password is None:
        alphabet = (
            string.ascii_letters +
            string.digits +
            "!@#$%^&*-_=+?"
        )

        newPassword = "".join(secrets.choice(alphabet) for _ in range(16))
    else: newPassword = admin_password
    hashed = hash_password(newPassword)

    admin_user = Staff(
        tenant_id=tenant.id,
        login = admin_login,
        firstname=admin_firstname,
        staff_type="administrator",
        hashed_password = hashed,
        actor_id = actor.id
    )
    db.add(admin_user)
    
    await db.refresh(tenant)
    return {
        "tenant": tenant, "login": admin_login, "password": newPassword
    }