from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import (
    ForeignKeyConstraint,
    Index,
    String,
    Boolean,
    BigInteger,
    Integer,
    Date,
    UniqueConstraint,
    func, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date

from src.database.base import BaseFields

if TYPE_CHECKING:
    from src.repository.service.service_model import Service

class Specialization(BaseFields):
    __tablename__ = "specializations"
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index(
            "uq_specialization_name_lower",
            func.lower(name),
            "tenant_id",
            unique=True
        ),
        UniqueConstraint("id", "tenant_id", name="uq_specialization_id_tenant"),
        ForeignKeyConstraint(
            ["created_by_actor_id", "tenant_id"],
            ["actors.id", "actors.tenant_id"],
            ondelete = "SET NULL (created_by_actor_id)",
            name = "fk_specializations_created_by_tenant"
        ),
    )

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="specialization",
        primaryjoin="and_(Employee.specialization_id == Specialization.id, Employee.tenant_id == Specialization.tenant_id)",
        foreign_keys = "[Employee.specialization_id]",
        lazy = "raise"
    )

    ALLOWED_FILTERS = {"name", "archived"}

class EmployeeServices(BaseFields):
    __tablename__ = "employee_services"

    employee_id: Mapped[int] = mapped_column(Integer)
    service_id: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("employee_id", "service_id", name="pk_employee_services"),
        ForeignKeyConstraint(
            ["employee_id", "tenant_id"],
            ["employees.id", "employees.tenant_id"],
            ondelete="CASCADE",
            name="fk_employee_services_to_employee"
        ),
        ForeignKeyConstraint(
            ["service_id", "tenant_id"],
            ["services.id", "services.tenant_id"],
            ondelete="CASCADE",
            name="fk_employee_services_to_service"
        ),
        ForeignKeyConstraint(
            ["created_by_actor_id", "tenant_id"],
            ["actors.id", "actors.tenant_id"],
            ondelete = "SET NULL (created_by_actor_id)",
            name = "fk_employee_services_created_by_tenant"
        ),
    )

class Employee(BaseFields):
    __tablename__ = "employees"

    firstname: Mapped[str] = mapped_column(String(255))
    lastname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    middlename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    birth_date: Mapped[date] = mapped_column(Date)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    specialization_id: Mapped[int | None] = mapped_column(Integer, nullable = True)
    specialization: Mapped["Specialization"] = relationship(
        back_populates="employees",
        primaryjoin="and_(Employee.specialization_id == Specialization.id, Employee.tenant_id == Specialization.tenant_id)",
        foreign_keys = [specialization_id],
        lazy = "raise"
    )

    services: Mapped[list["Service"]] = relationship(
        secondary = EmployeeServices.__table__,
        back_populates="employees",
        primaryjoin = "and_(Employee.id == foreign(employee_services.c.employee_id), Employee.tenant_id == foreign(employee_services.c.tenant_id))",
        secondaryjoin = "and_(Service.id == foreign(employee_services.c.service_id), Service.tenant_id == foreign(employee_services.c.tenant_id))"
    )

    salary_fixed: Mapped[int] = mapped_column(BigInteger, default=0)
    percent_from_services: Mapped[int] = mapped_column(Integer, default=0)
    percent_from_sales: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable = True)

    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name = "uq_emplyoee_id_tenant"),
        UniqueConstraint("phone", "tenant_id", name = "uq_employee_phone"),
        ForeignKeyConstraint(
            ["specialization_id", "tenant_id"],
            ["specializations.id", "specializations.tenant_id"],
            ondelete="SET NULL (specialization_id)",
            name="fk_employee_specialization_tenant"
        ),
        ForeignKeyConstraint(
            ["created_by_actor_id", "tenant_id"],
            ["actors.id", "actors.tenant_id"],
            ondelete = "SET NULL (created_by_actor_id)",
            name = "fk_employees_created_by_tenant"
        ),
    )

    ALLOWED_FILTERS = {"firstname", "lastname", "middlename", "phone", "active", "specialization_id", "archived"}