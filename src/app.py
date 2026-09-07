from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.core.admin.setup import init_admin
from src.core.exceptions import register_exception_handlers
from src.database.audit_listener import register_audit_listener
from src.exceptions.base import BaseAppException
from src.routes import protected_router, open_router
from src.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    register_audit_listener()
    yield

app = FastAPI(lifespan = lifespan,
            title = "Beauty salon",
            swagger_ui_parameters = {
                "defaultModelsExpandDepth": -1
            })

app.add_middleware(
    CORSMiddleware,
    allow_origins = (["*"] if settings.ENVIRONMENT == "development" 
                     else ["https://crm.osipovich.uz",
                           "https://api.osipovich.uz"]),
    allow_credentials = True,
    allow_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers = ["Content-Type", "Authorization"]
)

register_exception_handlers(app)

app.include_router(open_router)
app.include_router(protected_router)

init_admin(app)

@app.get("/health",
         status_code = 200,
         summary = "Проверка работоспособности",
         description = "Технический эндпоинт для проверки, что сервис запущен и отвечает на запросы.",
         dependencies = [])
async def root_path(): return "healthy"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    
    formatted_errors = [
        {
            "field": " -> ".join(map(str, err["loc"])), 
            "message": err["msg"]
        }
        for err in raw_errors
    ]

    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "detail": "Request data validation failed",
            "metadata": {
                "field": formatted_errors[0]["field"],
                "message": formatted_errors[0]["message"]
            }
        }
    )

@app.exception_handler(BaseAppException)
async def global_app_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(
        status_code = exc.statusCode,
        content={
            "error_code": exc.errorCode,
            "detail": exc.detail,
            "metadata": exc.metadata
        }
    )