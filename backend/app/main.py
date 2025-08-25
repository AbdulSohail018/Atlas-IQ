"""
Glonav FastAPI Application
Global Policy & Knowledge Navigator
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.core.database import init_databases, close_databases
from app.services.llm_service import LLMService
from app.services.knowledge_graph import KnowledgeGraphService

# Setup logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Glonav application...")
    
    # Initialize databases
    await init_databases()
    
    # Initialize services
    app.state.llm_service = LLMService()
    app.state.kg_service = KnowledgeGraphService()
    
    logger.info("Application startup complete")
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    await close_databases()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Glonav API",
    description="Global Policy & Knowledge Navigator - A unified platform for policy and public data analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Glonav API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        # TODO: Add actual health checks for databases
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "services": {
                "api": "healthy",
                "database": "healthy",  # TODO: Check actual DB connection
                "neo4j": "healthy",     # TODO: Check actual Neo4j connection
                "redis": "healthy",     # TODO: Check actual Redis connection
                "llm": "healthy"        # TODO: Check actual LLM service
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )