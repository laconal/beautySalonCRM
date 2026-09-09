from enum import StrEnum
from sqlalchemy import ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.database.base import BaseFields

class StaffType(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"

class StaffAuthAttempts(BaseFields):
    __tablename__ = "staff_auth_attempts"

    staff_id: Mapped[int] = mapped_column(Integer, index = True)
    ip: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), index = True)

    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name = "uq_staffAuthAttempts_tenant"),
        ForeignKeyConstraint(
            ["staff_id", "tenant_id"],
            ["staffs.id", "staffs.tenant_id"],
            ondelete = "CASCADE",
            name = "fk_staff_auth_attempts"
        )
    )

    ALLOWED_FILTERS = {"ip", "status", "created_at", "updated_at"}