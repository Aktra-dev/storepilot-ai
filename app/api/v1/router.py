"""
API v1 router aggregator.

Combines all module routers under a single router mounted at
settings.API_V1_PREFIX (see app/main.py). Each module currently exposes
an empty router — endpoints will be filled in as each module is built.
"""

from fastapi import APIRouter

from app.modules.ai_engine.router import router as ai_engine_router
from app.modules.approvals.router import router as approvals_router
from app.modules.auth.router import router as auth_router
from app.modules.inventory.router import router as inventory_router
from app.modules.operational_analysis.router import router as operational_analysis_router
from app.modules.products.router import router as products_router
from app.modules.sales.router import router as sales_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(products_router, prefix="/products", tags=["Products"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(sales_router, prefix="/sales", tags=["Sales"])
api_router.include_router(
    operational_analysis_router, prefix="/analysis", tags=["Operational Analysis"]
)
api_router.include_router(ai_engine_router, prefix="/ai", tags=["AI Engine"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["Approvals"])
