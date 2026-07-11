"""
StorePilot AI — application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers

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
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
