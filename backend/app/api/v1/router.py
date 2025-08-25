"""
Main API router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, datasets, graph, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])