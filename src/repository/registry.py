from typing import Type
from src.database.base import BaseFields
from datetime import date, datetime
from typing import Any, Type
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase
from src.repository import *

def build_model_registry(base_models: list[Type[BaseFields]]) -> dict[str, Type[BaseFields]]:
    registry = {}
    for model in base_models:
        key = model.__tablename__
        registry[key] = model
    return registry

MODEL_REGISTRY = build_model_registry([Employee, Service, Client, Appointment,
    Material, Receipt, Payout, Transaction, Notification, ServiceCategory, 
    WorkSchedule, EmployeeAbsence, Role, Promotion, GiftCard, StaffAuthAttempts])

_TYPE_MAP = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
    date: "date",
    datetime: "datetime",
}

def get_filter_schema(model: Type[DeclarativeBase]) -> list[dict[str, Any]]:
    allowed_fields = getattr(model, "ALLOWED_FILTERS", set())
    schema = []

    for field_name in sorted(allowed_fields):
        column = getattr(model, field_name, None)
        if column is None:
            continue  # guards against stale field names in ALLOWED_FILTERS

        col_type = column.property.columns[0].type
        entry: dict[str, Any] = {"field": field_name}

        if isinstance(col_type, SQLEnum) and col_type.enum_class is not None:
            entry["type"] = "enum"
            entry["options"] = [m.value for m in col_type.enum_class]
        else:
            entry["type"] = _TYPE_MAP.get(col_type.python_type, "string")

        schema.append(entry)

    return schema