"""
Application configuration
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseSettings, validator
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic app config
    APP_NAME: str = "Glonav"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database configurations
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/glonav"
    VECTOR_DB_URL: str = "postgresql://postgres:password@localhost:5432/glonav_vectors"
    DUCKDB_PATH: str = "data/warehouse/glonav.duckdb"
    
    # Neo4j configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # LLM configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Fallback LLM APIs
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Prefect configuration
    PREFECT_API_URL: str = "http://localhost:4200/api"
    
    # External APIs
    EPA_API_KEY: Optional[str] = None
    CENSUS_API_KEY: Optional[str] = None
    WHO_API_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Data paths
    DATA_RAW_PATH: str = "data/raw"
    DATA_PROCESSED_PATH: str = "data/processed"
    DATA_WAREHOUSE_PATH: str = "data/warehouse"
    
    # Performance settings
    MAX_WORKERS: int = 4
    CACHE_TTL: int = 3600  # 1 hour
    REQUEST_TIMEOUT: int = 30
    
    # RAG settings
    MAX_CONTEXT_LENGTH: int = 8000
    RETRIEVAL_TOP_K: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_PORT: int = 9090
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL"""
    return settings.DATABASE_URL


def get_vector_db_url() -> str:
    """Get vector database URL"""
    return settings.VECTOR_DB_URL


def get_neo4j_config() -> Dict[str, str]:
    """Get Neo4j configuration"""
    return {
        "uri": settings.NEO4J_URI,
        "user": settings.NEO4J_USER,
        "password": settings.NEO4J_PASSWORD
    }


def get_redis_config() -> str:
    """Get Redis configuration"""
    return settings.REDIS_URL


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration"""
    return {
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "openai_api_key": settings.OPENAI_API_KEY,
        "google_api_key": settings.GOOGLE_API_KEY,
        "max_context_length": settings.MAX_CONTEXT_LENGTH,
        "retrieval_top_k": settings.RETRIEVAL_TOP_K,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD
    }