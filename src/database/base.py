from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Generic, TypeVar, get_args, get_origin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, and_, func, select, text, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, foreign, mapped_column, relationship, validates
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.mixins import TenantMixin
from src.database.session import get_repository_db

if TYPE_CHECKING:
    from src.repository.staff.staff_model import Staff

class Base(DeclarativeBase):
    pass

class ActorType(StrEnum):
    STAFF = "staff"
    SYSTEM = "system"
    API = "api"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"

class Actor(TenantMixin, Base):
    __tablename__ = "actors"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(50))
    name: Mapped[str | None] = mapped_column(String(255), nullable = True)
    description: Mapped[str | None] = mapped_column(Text, nullable = True)

    staff: Mapped["Staff | None"] = relationship(
        back_populates="actor",
        primaryjoin="and_(Staff.actor_id == Actor.id, Staff.tenant_id == Actor.tenant_id)",
        foreign_keys="[Staff.actor_id]",
        lazy = "joined")

    @property
    def display_name(self) -> str:
        if self.actor_type == ActorType.STAFF:
            if "staff" in self.__dict__ and self.staff is not None:
                return f"{self.staff.login} ({self.staff.firstname})"
            return self.name or f"Сотрудник #{self.id}"            
        return self.name or (self.actor_type if hasattr(self.actor_type) else str(self.actor_type))

    __table_args__ = (UniqueConstraint("id", "tenant_id", name = "uq_actor_tenant"),)

class BaseFields(TenantMixin, Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    archived: Mapped[bool] = mapped_column(Boolean, default = False, server_default = text("false"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by_actor_id: Mapped[int | None] = mapped_column(Integer, nullable = True)
    
    @declared_attr
    def creator(cls):
        return relationship(
            "Actor",
            primaryjoin=lambda: and_(
                foreign(cls.created_by_actor_id) == Actor.id,
                cls.tenant_id == Actor.tenant_id,
            ),
            viewonly=True,
            lazy="selectin",
        )
    
    @property
    def created_by(self) -> dict | None:
        # 1. If the creator relationship is loaded and exists, use it!
        if self.creator:
            return {
                "id": self.creator.id,
                "display_name": self.creator.display_name,
                "actor_type": self.creator.actor_type
            }
        
        # 2. Fallback if there is no actor (e.g., system-created)
        # Note: Ensure "system" is a valid value in your ActorType Enum so Pydantic can parse it.
        return {
            "id": self.created_by_actor_id or 0,
            "display_name": "Неизвестная система",
            "actor_type": "system"  # Fixed key name from "type" to "actor_type"
        }

    @validates("created_by_actor_id")
    def validate_created_by(self, key, value):
        # Fixed: Compare the integer ID, not the dictionary property
        if self.id is not None and self.created_by_actor_id is not None:
            if self.created_by_actor_id != value:
                raise ValueError("Запрещено изменять создателя объекта")
        return value
            
    @validates("created_at")
    def validate_created_at(self, key, value):
        if self.id is not None and self.created_at is not None:
            current_val = self.created_at.astimezone() if hasattr(self.created_at, 'astimezone') else self.created_at
            new_val = value.astimezone() if hasattr(value, 'astimezone') else value
            if current_val != new_val:
                raise ValueError("Запрещено изменять дату создания объекта")

T = TypeVar('T')

class BaseRepository(Generic[T]):
    model: type[T]

    def __init_subclass__(cls):
        super().__init_subclass__()

        for base in getattr(cls, "__orig_bases__", ()):
            if get_origin(base) is BaseRepository:
                cls.model = get_args(base)[0]
                break

    @property
    def db(self) -> AsyncSession:
        return get_repository_db()

    async def get(self, id: int) -> T | None:
        """returns None if object with provided ID does not exists"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, id: int, **fields: Any) -> T | None:
        """returns None if object with provided ID does not exists"""
        try:
            obj = await self.get(id)
            if not obj: return None

            for name, value in fields.items():
                if not hasattr(obj, name):
                    raise AttributeError(
                        f"{self.model.__name__} has no field '{name}'"
                    )
                setattr(obj, name, value)

            await self.db.flush()
            await self.db.refresh(obj)
            return obj
        except Exception as e:
            raise e

    async def archive(self, id: int) -> T | None:
        return self.update(id, archived = True)
            
    async def delete(self, id: int) -> bool:
        """returns None if object with provided ID does not exists"""
        obj = await self.get(id)
        if not obj: return False

        await self.db.delete(obj)
        return True