"""
Health check endpoint.

GET /api/health -> used to verify the service is up and responding.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "StorePilot AI",
    }
