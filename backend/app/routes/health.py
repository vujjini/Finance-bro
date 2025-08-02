# backend/app/routes/health.py
from fastapi import APIRouter
from datetime import datetime, timezone
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": os.getenv("API_VERSION", "v1"),
        "app": os.getenv("APP_NAME")
    }

# Once actual external DBs are started to use update the health checks to see if CRUD operations to those DBs are good. Could also have health checks for other external services if possible
@router.get("/health/detailed")
async def detailed_health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "services": {
            "api": "healthy",
            "auth": "healthy",
            "vector_store": "not_connected",  # Will update later
            "database": "in_memory"
        }
    }