"""
Database connections and initialization
"""

import asyncio
from typing import AsyncGenerator, Optional
import asyncpg
import duckdb
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# SQLAlchemy Base
Base = declarative_base()

# Global connection pools and clients
postgres_engine = None
vector_engine = None
neo4j_driver = None
redis_client = None
duckdb_conn = None
AsyncSessionLocal = None


async def init_databases():
    """Initialize all database connections"""
    global postgres_engine, vector_engine, neo4j_driver, redis_client, duckdb_conn, AsyncSessionLocal
    
    try:
        # PostgreSQL for main database
        postgres_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        # PostgreSQL with pgvector for vector search
        vector_engine = create_async_engine(
            settings.VECTOR_DB_URL,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10
        )
        
        # Session factory
        AsyncSessionLocal = async_sessionmaker(
            postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Neo4j for graph database
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
        # Redis for caching
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # DuckDB for analytics
        duckdb_conn = duckdb.connect(settings.DUCKDB_PATH)
        
        # Test connections
        await test_connections()
        
        logger.info("All database connections initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize databases", error=str(e))
        raise


async def close_databases():
    """Close all database connections"""
    global postgres_engine, vector_engine, neo4j_driver, redis_client, duckdb_conn
    
    try:
        if postgres_engine:
            await postgres_engine.dispose()
        
        if vector_engine:
            await vector_engine.dispose()
        
        if neo4j_driver:
            await neo4j_driver.close()
        
        if redis_client:
            await redis_client.close()
        
        if duckdb_conn:
            duckdb_conn.close()
        
        logger.info("All database connections closed")
        
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


async def test_connections():
    """Test all database connections"""
    
    # Test PostgreSQL
    async with postgres_engine.begin() as conn:
        result = await conn.execute("SELECT 1")
        assert result.scalar() == 1
    
    # Test Neo4j
    async with neo4j_driver.session() as session:
        result = await session.run("RETURN 1 as num")
        record = await result.single()
        assert record["num"] == 1
    
    # Test Redis
    await redis_client.ping()
    
    # Test DuckDB
    result = duckdb_conn.execute("SELECT 1").fetchone()
    assert result[0] == 1
    
    logger.info("All database connections tested successfully")


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Get PostgreSQL session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_vector_session() -> AsyncGenerator[AsyncSession, None]:
    """Get vector database session"""
    SessionLocal = async_sessionmaker(vector_engine, class_=AsyncSession)
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_neo4j_session():
    """Get Neo4j session"""
    return neo4j_driver.session()


async def get_redis_client():
    """Get Redis client"""
    return redis_client


def get_duckdb_connection():
    """Get DuckDB connection"""
    return duckdb_conn


class DatabaseManager:
    """Database manager for handling multiple database operations"""
    
    def __init__(self):
        self.postgres_engine = postgres_engine
        self.vector_engine = vector_engine
        self.neo4j_driver = neo4j_driver
        self.redis_client = redis_client
        self.duckdb_conn = duckdb_conn
    
    async def execute_postgres(self, query: str, params: dict = None):
        """Execute PostgreSQL query"""
        async with get_postgres_session() as session:
            result = await session.execute(query, params or {})
            await session.commit()
            return result
    
    async def execute_neo4j(self, query: str, params: dict = None):
        """Execute Neo4j query"""
        async with self.neo4j_driver.session() as session:
            result = await session.run(query, params or {})
            return [record async for record in result]
    
    async def cache_set(self, key: str, value: str, expire: int = None):
        """Set cache value in Redis"""
        await self.redis_client.set(key, value, ex=expire)
    
    async def cache_get(self, key: str) -> Optional[str]:
        """Get cache value from Redis"""
        value = await self.redis_client.get(key)
        return value.decode() if value else None
    
    def execute_duckdb(self, query: str, params: tuple = None):
        """Execute DuckDB query"""
        if params:
            return self.duckdb_conn.execute(query, params)
        return self.duckdb_conn.execute(query)


# Global database manager instance
db_manager = DatabaseManager()