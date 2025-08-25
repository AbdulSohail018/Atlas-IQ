"""
Datasets API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
import structlog

from app.models.base import DatasetInfo, PagedResponse
from app.core.database import get_duckdb_connection, get_postgres_session
from app.services.rag_service import RAGService

logger = structlog.get_logger()
router = APIRouter()


async def get_rag_service() -> RAGService:
    """Dependency to get RAG service"""
    return RAGService()


@router.get("/", response_model=PagedResponse)
async def list_datasets(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search datasets by name or description"),
    source: Optional[str] = Query(None, description="Filter by data source"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags")
):
    """
    List all available datasets with pagination and filtering
    """
    
    try:
        # Build query conditions
        conditions = ["is_active = true"]
        params = {}
        
        if search:
            conditions.append("(name ILIKE %(search)s OR description ILIKE %(search)s)")
            params["search"] = f"%{search}%"
        
        if source:
            conditions.append("source = %(source)s")
            params["source"] = source
        
        if tags:
            # JSON array contains any of the specified tags
            tag_conditions = []
            for i, tag in enumerate(tags):
                tag_key = f"tag_{i}"
                tag_conditions.append(f"tags::text ILIKE %({tag_key})s")
                params[tag_key] = f"%{tag}%"
            conditions.append(f"({' OR '.join(tag_conditions)})")
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM datasets WHERE {where_clause}"
        
        # Get paginated results
        offset = (page - 1) * size
        data_query = f"""
        SELECT id, name, description, source, source_url, schema_info, 
               record_count, tags, metadata, created_at, updated_at
        FROM datasets 
        WHERE {where_clause}
        ORDER BY updated_at DESC
        LIMIT %(size)s OFFSET %(offset)s
        """
        
        params.update({"size": size, "offset": offset})
        
        async with get_postgres_session() as session:
            # Get total count
            count_result = await session.execute(count_query, params)
            total = count_result.scalar()
            
            # Get data
            data_result = await session.execute(data_query, params)
            rows = data_result.fetchall()
            
            datasets = []
            for row in rows:
                dataset = DatasetInfo(
                    id=row.id,
                    name=row.name,
                    description=row.description or "",
                    source=row.source,
                    schema_info=row.schema_info or {},
                    last_updated=row.updated_at,
                    record_count=row.record_count,
                    tags=row.tags or []
                )
                datasets.append(dataset)
            
            return PagedResponse(
                items=datasets,
                total=total,
                page=page,
                size=size,
                has_next=(offset + size) < total,
                has_prev=page > 1
            )
    
    except Exception as e:
        logger.error("Error listing datasets", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve datasets")


@router.get("/{dataset_id}", response_model=DatasetInfo)
async def get_dataset(dataset_id: str):
    """
    Get detailed information about a specific dataset
    """
    
    try:
        query = """
        SELECT id, name, description, source, source_url, schema_info, 
               record_count, tags, metadata, created_at, updated_at
        FROM datasets 
        WHERE id = %(dataset_id)s AND is_active = true
        """
        
        async with get_postgres_session() as session:
            result = await session.execute(query, {"dataset_id": dataset_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Dataset not found")
            
            return DatasetInfo(
                id=row.id,
                name=row.name,
                description=row.description or "",
                source=row.source,
                schema_info=row.schema_info or {},
                last_updated=row.updated_at,
                record_count=row.record_count,
                tags=row.tags or []
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving dataset", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dataset")


@router.get("/{dataset_id}/sample")
async def get_dataset_sample(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of sample rows")
):
    """
    Get sample data from a dataset
    """
    
    try:
        # First verify dataset exists
        dataset_query = """
        SELECT name, schema_info FROM datasets 
        WHERE id = %(dataset_id)s AND is_active = true
        """
        
        async with get_postgres_session() as session:
            dataset_result = await session.execute(dataset_query, {"dataset_id": dataset_id})
            dataset_row = dataset_result.fetchone()
            
            if not dataset_row:
                raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get sample data from DuckDB
        try:
            duckdb_conn = get_duckdb_connection()
            
            # Construct table name (assuming it's derived from dataset name)
            table_name = dataset_row.name.lower().replace(" ", "_").replace("-", "_")
            
            sample_query = f"""
            SELECT * FROM {table_name} 
            LIMIT {limit}
            """
            
            result = duckdb_conn.execute(sample_query).fetchall()
            columns = [desc[0] for desc in duckdb_conn.description] if duckdb_conn.description else []
            
            # Convert to list of dictionaries
            sample_data = []
            for row in result:
                row_dict = dict(zip(columns, row))
                sample_data.append(row_dict)
            
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_row.name,
                "sample_size": len(sample_data),
                "columns": columns,
                "data": sample_data,
                "schema": dataset_row.schema_info or {}
            }
        
        except Exception as e:
            logger.warning("Failed to get sample from DuckDB", error=str(e))
            # Return empty sample if table doesn't exist
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_row.name,
                "sample_size": 0,
                "columns": [],
                "data": [],
                "schema": dataset_row.schema_info or {},
                "note": "Sample data not available - dataset may not be fully processed"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving dataset sample", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve sample data")


@router.get("/{dataset_id}/schema")
async def get_dataset_schema(dataset_id: str):
    """
    Get schema information for a dataset
    """
    
    try:
        query = """
        SELECT name, schema_info, metadata FROM datasets 
        WHERE id = %(dataset_id)s AND is_active = true
        """
        
        async with get_postgres_session() as session:
            result = await session.execute(query, {"dataset_id": dataset_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Dataset not found")
            
            return {
                "dataset_id": dataset_id,
                "dataset_name": row.name,
                "schema": row.schema_info or {},
                "metadata": row.metadata or {},
                "last_updated": datetime.utcnow().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving dataset schema", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve schema")


@router.get("/{dataset_id}/stats")
async def get_dataset_statistics(dataset_id: str):
    """
    Get statistical summary of a dataset
    """
    
    try:
        # Get dataset info
        dataset_query = """
        SELECT name, record_count, schema_info FROM datasets 
        WHERE id = %(dataset_id)s AND is_active = true
        """
        
        async with get_postgres_session() as session:
            dataset_result = await session.execute(dataset_query, {"dataset_id": dataset_id})
            dataset_row = dataset_result.fetchone()
            
            if not dataset_row:
                raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get statistics from DuckDB
        try:
            duckdb_conn = get_duckdb_connection()
            table_name = dataset_row.name.lower().replace(" ", "_").replace("-", "_")
            
            # Get basic statistics
            stats_query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT *) as unique_rows
            FROM {table_name}
            """
            
            stats_result = duckdb_conn.execute(stats_query).fetchone()
            
            # Get column information
            describe_query = f"DESCRIBE {table_name}"
            describe_result = duckdb_conn.execute(describe_query).fetchall()
            
            columns_info = []
            for col_info in describe_result:
                columns_info.append({
                    "name": col_info[0],
                    "type": col_info[1],
                    "null": col_info[2] if len(col_info) > 2 else None,
                    "key": col_info[3] if len(col_info) > 3 else None,
                    "default": col_info[4] if len(col_info) > 4 else None,
                    "extra": col_info[5] if len(col_info) > 5 else None
                })
            
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_row.name,
                "total_rows": stats_result[0] if stats_result else 0,
                "unique_rows": stats_result[1] if stats_result else 0,
                "columns": columns_info,
                "schema_info": dataset_row.schema_info or {},
                "last_calculated": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.warning("Failed to get stats from DuckDB", error=str(e))
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset_row.name,
                "total_rows": dataset_row.record_count or 0,
                "columns": [],
                "schema_info": dataset_row.schema_info or {},
                "note": "Detailed statistics not available",
                "last_calculated": datetime.utcnow().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving dataset statistics", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/search/text")
async def search_datasets_content(
    query: str = Query(..., description="Search query"),
    datasets: Optional[List[str]] = Query(None, description="Limit search to specific datasets"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Search within dataset content using RAG
    """
    
    try:
        # Build filters for RAG service
        filters = {}
        if datasets:
            filters["dataset_id"] = {"$in": datasets}
        
        # Perform RAG search
        search_results = await rag_service.retrieve_context(
            query=query,
            top_k=limit,
            include_graph_context=False,
            filters=filters
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "id": result["id"],
                "title": result.get("title", "Untitled"),
                "content_excerpt": result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"],
                "source": result.get("source", "Unknown"),
                "score": result.get("score", 0.0),
                "retrieval_method": result.get("retrieval_method", "unknown"),
                "metadata": result.get("metadata", {})
            })
        
        return {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error searching dataset content", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search content")


@router.get("/sources")
async def list_data_sources():
    """
    List all available data sources
    """
    
    try:
        query = """
        SELECT source, COUNT(*) as dataset_count, 
               MIN(created_at) as first_added,
               MAX(updated_at) as last_updated
        FROM datasets 
        WHERE is_active = true
        GROUP BY source
        ORDER BY dataset_count DESC
        """
        
        async with get_postgres_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            
            sources = []
            for row in rows:
                sources.append({
                    "source": row.source,
                    "dataset_count": row.dataset_count,
                    "first_added": row.first_added,
                    "last_updated": row.last_updated
                })
            
            return {
                "sources": sources,
                "total_sources": len(sources),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error("Error listing data sources", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sources")


@router.get("/tags")
async def list_dataset_tags():
    """
    List all available dataset tags
    """
    
    try:
        query = """
        SELECT DISTINCT jsonb_array_elements_text(tags) as tag
        FROM datasets 
        WHERE is_active = true AND tags IS NOT NULL
        """
        
        async with get_postgres_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            
            tags = [row.tag for row in rows if row.tag]
            tags.sort()
            
            return {
                "tags": tags,
                "total_tags": len(tags),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error("Error listing dataset tags", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list tags")


@router.get("/summary")
async def get_datasets_summary(rag_service: RAGService = Depends(get_rag_service)):
    """
    Get summary statistics for all datasets
    """
    
    try:
        # Get basic dataset counts
        summary_query = """
        SELECT 
            COUNT(*) as total_datasets,
            COUNT(DISTINCT source) as unique_sources,
            SUM(record_count) as total_records,
            AVG(record_count) as avg_records_per_dataset,
            MIN(created_at) as oldest_dataset,
            MAX(updated_at) as newest_update
        FROM datasets 
        WHERE is_active = true
        """
        
        async with get_postgres_session() as session:
            result = await session.execute(summary_query)
            row = result.fetchone()
            
            # Get RAG statistics
            rag_stats = await rag_service.get_retrieval_stats()
            
            return {
                "datasets": {
                    "total": row.total_datasets or 0,
                    "unique_sources": row.unique_sources or 0,
                    "total_records": row.total_records or 0,
                    "avg_records": float(row.avg_records_per_dataset or 0),
                    "oldest_dataset": row.oldest_dataset,
                    "newest_update": row.newest_update
                },
                "retrieval_system": rag_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error("Error getting datasets summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get summary")