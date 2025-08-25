"""
Knowledge Graph API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
import structlog

from app.services.knowledge_graph import KnowledgeGraphService
from app.models.base import Citation

logger = structlog.get_logger()
router = APIRouter()


async def get_kg_service() -> KnowledgeGraphService:
    """Dependency to get Knowledge Graph service"""
    return KnowledgeGraphService()


@router.get("/query")
async def query_graph(
    cypher: str = Query(..., description="Cypher query to execute"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Execute a Cypher query against the knowledge graph
    """
    
    try:
        # Add LIMIT to query if not present
        cypher_lower = cypher.lower().strip()
        if not cypher_lower.endswith(';'):
            cypher += ';'
        
        if 'limit' not in cypher_lower:
            cypher = cypher.rstrip(';') + f' LIMIT {limit};'
        
        # Execute query using Neo4j session directly
        from app.core.database import get_neo4j_session
        
        async with get_neo4j_session() as session:
            result = await session.run(cypher)
            
            records = []
            async for record in result:
                # Convert Neo4j record to dictionary
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Neo4j types to JSON-serializable types
                    if hasattr(value, '__dict__'):
                        record_dict[key] = dict(value)
                    else:
                        record_dict[key] = value
                records.append(record_dict)
            
            return {
                "query": cypher,
                "results": records,
                "count": len(records),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error("Error executing graph query", query=cypher, error=str(e))
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


@router.get("/entities/search")
async def search_entities(
    query: str = Query(..., description="Search text"),
    types: Optional[List[str]] = Query(None, description="Entity types to filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Search for entities in the knowledge graph
    """
    
    try:
        entities = await kg_service.search_entities(
            query_text=query,
            entity_types=types,
            limit=limit
        )
        
        return {
            "query": query,
            "entity_types": types,
            "entities": entities,
            "count": len(entities),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error searching entities", query=query, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search entities")


@router.get("/entities/{entity_id}")
async def get_entity_details(
    entity_id: str,
    context_depth: int = Query(2, ge=1, le=5, description="Context depth"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get detailed information about a specific entity
    """
    
    try:
        entity_context = await kg_service.get_entity_context(
            entity_id=entity_id,
            context_depth=context_depth
        )
        
        if not entity_context:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return {
            "entity_id": entity_id,
            "context": entity_context,
            "context_depth": context_depth,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting entity details", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get entity details")


@router.get("/entities/{entity_id}/related")
async def get_related_entities(
    entity_id: str,
    relationship_types: Optional[List[str]] = Query(None, description="Relationship types to filter"),
    max_depth: int = Query(2, ge=1, le=5, description="Maximum traversal depth"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get entities related to a specific entity
    """
    
    try:
        related_entities = await kg_service.find_related_entities(
            entity_id=entity_id,
            relationship_types=relationship_types,
            max_depth=max_depth,
            limit=limit
        )
        
        return {
            "entity_id": entity_id,
            "relationship_types": relationship_types,
            "max_depth": max_depth,
            "related_entities": related_entities,
            "count": len(related_entities),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error getting related entities", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get related entities")


@router.get("/path/{start_id}/{end_id}")
async def find_path_between_entities(
    start_id: str,
    end_id: str,
    max_length: int = Query(5, ge=1, le=10, description="Maximum path length"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Find shortest path between two entities
    """
    
    try:
        paths = await kg_service.find_path_between_entities(
            start_id=start_id,
            end_id=end_id,
            max_length=max_length
        )
        
        return {
            "start_id": start_id,
            "end_id": end_id,
            "max_length": max_length,
            "paths": paths,
            "path_count": len(paths),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error finding path", start_id=start_id, end_id=end_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to find path")


@router.get("/statistics")
async def get_graph_statistics(kg_service: KnowledgeGraphService = Depends(get_kg_service)):
    """
    Get knowledge graph statistics
    """
    
    try:
        stats = await kg_service.get_entity_statistics()
        
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error getting graph statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.post("/entities")
async def create_entity(
    entity_data: Dict[str, Any],
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Create a new entity in the knowledge graph
    """
    
    try:
        entity_type = entity_data.pop("type", "Entity")
        properties = entity_data
        
        entity_id = await kg_service.create_entity(
            entity_type=entity_type,
            properties=properties
        )
        
        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "properties": properties,
            "status": "created",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error creating entity", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create entity")


@router.post("/relationships")
async def create_relationship(
    relationship_data: Dict[str, Any],
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Create a relationship between entities
    """
    
    try:
        from_id = relationship_data.get("from_id")
        to_id = relationship_data.get("to_id")
        relationship_type = relationship_data.get("type", "RELATED")
        properties = relationship_data.get("properties", {})
        
        if not from_id or not to_id:
            raise HTTPException(status_code=400, detail="from_id and to_id are required")
        
        success = await kg_service.create_relationship(
            from_id=from_id,
            to_id=to_id,
            relationship_type=relationship_type,
            properties=properties
        )
        
        if success:
            return {
                "from_id": from_id,
                "to_id": to_id,
                "relationship_type": relationship_type,
                "properties": properties,
                "status": "created",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create relationship")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating relationship", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create relationship")


@router.post("/citations/graph")
async def build_citation_graph(
    citations: List[Dict[str, Any]],
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Build a graph showing relationships between citations
    """
    
    try:
        # Convert to Citation objects
        citation_objects = []
        for cite_data in citations:
            citation = Citation(
                id=cite_data.get("id", ""),
                title=cite_data.get("title", ""),
                source=cite_data.get("source", ""),
                excerpt=cite_data.get("excerpt", ""),
                confidence=cite_data.get("confidence", 0.8),
                metadata=cite_data.get("metadata", {})
            )
            citation_objects.append(citation)
        
        citation_graph = await kg_service.build_citation_graph(citation_objects)
        
        return {
            "citation_graph": citation_graph,
            "input_citations": len(citations),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error building citation graph", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to build citation graph")


@router.get("/visualization")
async def get_graph_visualization(
    entity_ids: Optional[List[str]] = Query(None, description="Entity IDs to include"),
    max_nodes: int = Query(50, ge=10, le=200, description="Maximum nodes"),
    include_relationships: bool = Query(True, description="Include relationships"),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    Get graph data for visualization
    """
    
    try:
        # Build Cypher query for visualization
        if entity_ids:
            entity_filter = "WHERE n.id IN $entity_ids"
            params = {"entity_ids": entity_ids}
        else:
            entity_filter = ""
            params = {}
        
        # Get nodes
        nodes_query = f"""
        MATCH (n)
        {entity_filter}
        RETURN n, labels(n) as types
        LIMIT {max_nodes}
        """
        
        # Get relationships if requested
        if include_relationships:
            if entity_ids:
                rels_query = """
                MATCH (n)-[r]-(m)
                WHERE n.id IN $entity_ids OR m.id IN $entity_ids
                RETURN r, n.id as from_id, m.id as to_id, type(r) as rel_type
                LIMIT $max_rels
                """
                params["max_rels"] = max_nodes * 2
            else:
                rels_query = f"""
                MATCH (n)-[r]-(m)
                RETURN r, n.id as from_id, m.id as to_id, type(r) as rel_type
                LIMIT {max_nodes * 2}
                """
        
        from app.core.database import get_neo4j_session
        
        # Execute queries
        async with get_neo4j_session() as session:
            # Get nodes
            nodes_result = await session.run(nodes_query, params)
            nodes = []
            async for record in nodes_result:
                node = dict(record["n"])
                node["types"] = record["types"]
                nodes.append(node)
            
            # Get relationships
            edges = []
            if include_relationships:
                rels_result = await session.run(rels_query, params)
                async for record in rels_result:
                    edge = {
                        "from": record["from_id"],
                        "to": record["to_id"],
                        "type": record["rel_type"],
                        "properties": dict(record["r"]) if record["r"] else {}
                    }
                    edges.append(edge)
        
        return {
            "visualization": {
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges)
            },
            "parameters": {
                "entity_ids": entity_ids,
                "max_nodes": max_nodes,
                "include_relationships": include_relationships
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Error getting graph visualization", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get visualization data")