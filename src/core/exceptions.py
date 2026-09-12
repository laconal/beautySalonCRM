from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.background import BackgroundTask
from src.core.config import settings
from src.core.telegram_alerts import send_error_alert
from src.exceptions.base import BaseAppException

# async def sqlalchemy_integrity_exception_handler(request: Request, exc: IntegrityError):
#     error_msg = str(exc.orig).lower() if exc.orig else ""
    
#     if "unique constraint" in error_msg or "duplicate key" in error_msg:
#         raise BaseAppException(
#             detail = "Record with unique value already exists",
#             errorCode = "RECORD_UNIQUE_VALUE_VIOLANCE",
#             statusCode = 409
#         )

#     if "foreign key constraint" in error_msg:
#         raise BaseAppException(
#             detail = "Foreign key not found",
#             errorCode = "FOREIGN_KEY_NOT_FOUND",
#             statusCode = 404
#         )

#     raise BaseAppException(
#         detail = "Database integrity violance",
#         errorCode = "DATABASE_INTEGRITY_VIOLANCE",
#         statusCode = 409
#     )

async def sqlalchemy_integrity_exception_handler(
    request: Request,
    exc: IntegrityError,
):
    orig = exc.orig

    pgcode = getattr(orig, "pgcode", None)
    diag = getattr(orig, "diag", None)

    constraint_name = getattr(diag, "constraint_name", None)

    if pgcode == "23505":
        raise BaseAppException(
            detail="Record with unique value already exists",
            errorCode="RECORD_UNIQUE_VALUE_VIOLATION",
            statusCode=409,
        )

    if pgcode == "23503":
        raise BaseAppException(
            detail="Foreign key not found",
            errorCode="FOREIGN_KEY_NOT_FOUND",
            statusCode=404,
        )

    if pgcode == "23502":
        raise BaseAppException(
            detail="Required database field is missing",
            errorCode="DATABASE_NOT_NULL_VIOLATION",
            statusCode=409,
        )

    if pgcode == "23514":
        raise BaseAppException(
            detail="Database check constraint violated",
            errorCode="DATABASE_CHECK_VIOLATION",
            statusCode=409,
        )

    if pgcode == "23P01" and constraint_name == "excl_employee_appointment_overlap":
        raise BaseAppException(
            detail="Employee is busy during these hours",
            errorCode="EMPLOYEE_APPOINTMENT_TIME_CONFLICT",
            statusCode=409,
        )

    # Don't hide this during development
    print(
        "Unhandled IntegrityError:",
        {
            "pgcode": pgcode,
            "constraint": constraint_name,
            "orig": repr(orig),
        },
    ) if settings.ENVIRONMENT == "development" else print()

    raise BaseAppException(
        detail="Database integrity violation",
        errorCode="DATABASE_INTEGRITY_VIOLATION",
        statusCode=409,
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches anything with no more specific handler - i.e. every real 500 this
    app can produce, since no BaseAppException subclass uses statusCode=500.
    Sends a Telegram alert (see src/core/telegram_alerts.py) as a background
    task so a slow/broken bot token never delays the error response itself.
    """
    print(f"Unhandled exception on {request.method} {request.url.path}: {exc!r}")

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "detail": "Internal server error",
            "metadata": {},
        },
        background=BackgroundTask(send_error_alert, request, exc),
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, sqlalchemy_integrity_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)