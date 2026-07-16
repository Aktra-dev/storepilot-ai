"""
StorePilot AI — application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models_registry  # noqa: F401  (registers every model at startup)
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.modules.dashboard.router import router as dashboard_router
from app.modules.operational_analysis.operations_router import (
    router as operations_router,
)
from app.modules.tasks.router import router as tasks_router

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global exception handlers ---
register_exception_handlers(app)

# --- Routers ---
app.include_router(health_router, prefix="/api")
app.include_router(operations_router, prefix="/api/operations", tags=["Operations"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
