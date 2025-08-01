from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import os
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Stock Portfolio Analysis API",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service dependencies."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Stock Portfolio Analysis API",
        "version": "1.0.0",
        "dependencies": {}
    }
    
    try:
        # Check environment variables
        required_envs = [
            "POLYGON_API_KEY",
            "JWT_SECRET_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS"
        ]
        
        env_status = {}
        for env in required_envs:
            env_status[env] = "configured" if os.getenv(env) else "missing"
        
        health_status["dependencies"]["environment"] = env_status
        
        # Check vector store
        try:
            from app.utils.vector_store import get_vector_store
            vector_store = get_vector_store()
            health_status["dependencies"]["vector_store"] = "healthy"
        except Exception as e:
            health_status["dependencies"]["vector_store"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Polygon API
        try:
            from app.utils.polygon_client import get_polygon_client
            polygon_client = get_polygon_client()
            # Try a simple API call
            test_price = polygon_client.get_current_price("AAPL")
            health_status["dependencies"]["polygon_api"] = "healthy" if test_price else "error"
        except Exception as e:
            health_status["dependencies"]["polygon_api"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check LLM service
        try:
            from langchain.chat_models import init_chat_model
            llm = init_chat_model("gemini-2.0-flash-001", model_provider="google_vertexai")
            health_status["dependencies"]["llm_service"] = "healthy"
        except Exception as e:
            health_status["dependencies"]["llm_service"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in detailed health check: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Stock Portfolio Analysis API",
            "error": str(e)
        }

@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Perform essential service checks
        from app.utils.vector_store import get_vector_store
        vector_store = get_vector_store()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }