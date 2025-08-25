"""
Health check endpoints
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio
import structlog

from app.models.base import HealthStatus
from app.core.database import (
    postgres_engine, neo4j_driver, redis_client, duckdb_conn
)
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check for all services
    """
    
    try:
        # Check all services in parallel
        checks = await asyncio.gather(
            check_postgres(),
            check_neo4j(),
            check_redis(),
            check_duckdb(),
            check_ollama(),
            return_exceptions=True
        )
        
        service_names = ["postgres", "neo4j", "redis", "duckdb", "ollama"]
        services = {}
        
        overall_status = "healthy"
        
        for i, (service_name, check_result) in enumerate(zip(service_names, checks)):
            if isinstance(check_result, Exception):
                services[service_name] = "unhealthy"
                overall_status = "degraded"
                logger.warning(f"{service_name} health check failed", error=str(check_result))
            else:
                services[service_name] = "healthy" if check_result else "unhealthy"
                if not check_result:
                    overall_status = "degraded"
        
        # If any critical service is down, mark as unhealthy
        critical_services = ["postgres", "redis"]
        if any(services[svc] == "unhealthy" for svc in critical_services):
            overall_status = "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow().timestamp(),
            version=settings.VERSION,
            services=services
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Health check failed")


@router.get("/postgres")
async def check_postgres_health():
    """Check PostgreSQL database health"""
    
    try:
        is_healthy = await check_postgres()
        return {
            "service": "postgres",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("PostgreSQL health check failed", error=str(e))
        return {
            "service": "postgres",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/neo4j")
async def check_neo4j_health():
    """Check Neo4j database health"""
    
    try:
        is_healthy = await check_neo4j()
        return {
            "service": "neo4j",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Neo4j health check failed", error=str(e))
        return {
            "service": "neo4j",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/redis")
async def check_redis_health():
    """Check Redis health"""
    
    try:
        is_healthy = await check_redis()
        return {
            "service": "redis",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "service": "redis",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/duckdb")
async def check_duckdb_health():
    """Check DuckDB health"""
    
    try:
        is_healthy = await check_duckdb()
        return {
            "service": "duckdb",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("DuckDB health check failed", error=str(e))
        return {
            "service": "duckdb",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/ollama")
async def check_ollama_health():
    """Check Ollama LLM service health"""
    
    try:
        is_healthy = await check_ollama()
        return {
            "service": "ollama",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        return {
            "service": "ollama",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Helper functions for individual service checks

async def check_postgres() -> bool:
    """Check PostgreSQL connection"""
    try:
        if not postgres_engine:
            return False
        
        async with postgres_engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            return result.scalar() == 1
    except Exception:
        return False


async def check_neo4j() -> bool:
    """Check Neo4j connection"""
    try:
        if not neo4j_driver:
            return False
        
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 as num")
            record = await result.single()
            return record and record["num"] == 1
    except Exception:
        return False


async def check_redis() -> bool:
    """Check Redis connection"""
    try:
        if not redis_client:
            return False
        
        await redis_client.ping()
        return True
    except Exception:
        return False


async def check_duckdb() -> bool:
    """Check DuckDB connection"""
    try:
        if not duckdb_conn:
            return False
        
        result = duckdb_conn.execute("SELECT 1").fetchone()
        return result and result[0] == 1
    except Exception:
        return False


async def check_ollama() -> bool:
    """Check Ollama service"""
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False