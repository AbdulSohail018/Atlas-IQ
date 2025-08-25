"""
Knowledge Graph Service for Neo4j operations
"""

from typing import Dict, List, Any, Optional, Tuple
import asyncio
from datetime import datetime
import structlog
from neo4j import AsyncResult

from app.core.database import get_neo4j_session
from app.models.base import Citation

logger = structlog.get_logger()


class KnowledgeGraphService:
    """Service for knowledge graph operations"""
    
    def __init__(self):
        self.session = None
    
    async def initialize_schema(self):
        """Initialize Neo4j schema and constraints"""
        
        constraints_and_indexes = [
            # Constraints
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT region_id IF NOT EXISTS FOR (r:Region) REQUIRE r.id IS UNIQUE",
            
            # Indexes
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX dataset_name IF NOT EXISTS FOR (d:Dataset) ON (d.name)",
            "CREATE INDEX policy_title IF NOT EXISTS FOR (p:Policy) ON (p.title)",
            "CREATE INDEX region_name IF NOT EXISTS FOR (r:Region) ON (r.name)",
            "CREATE INDEX relationship_type IF NOT EXISTS FOR ()-[r]-() ON (r.type)",
        ]
        
        async with get_neo4j_session() as session:
            for query in constraints_and_indexes:
                try:
                    await session.run(query)
                    logger.debug("Created constraint/index", query=query)
                except Exception as e:
                    logger.warning("Failed to create constraint/index", query=query, error=str(e))
    
    async def create_entity(
        self,
        entity_type: str,
        properties: Dict[str, Any]
    ) -> str:
        """Create an entity in the knowledge graph"""
        
        query = f"""
        CREATE (e:{entity_type} $properties)
        RETURN e.id as id
        """
        
        # Ensure ID is set
        if 'id' not in properties:
            import uuid
            properties['id'] = str(uuid.uuid4())
        
        # Add timestamps
        properties['created_at'] = datetime.utcnow().isoformat()
        properties['updated_at'] = datetime.utcnow().isoformat()
        
        async with get_neo4j_session() as session:
            result = await session.run(query, properties=properties)
            record = await result.single()
            return record["id"] if record else properties['id']
    
    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a relationship between entities"""
        
        properties = properties or {}
        properties['created_at'] = datetime.utcnow().isoformat()
        
        query = """
        MATCH (a), (b)
        WHERE a.id = $from_id AND b.id = $to_id
        CREATE (a)-[r:RELATED $properties]->(b)
        SET r.type = $relationship_type
        RETURN r
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(
                query,
                from_id=from_id,
                to_id=to_id,
                relationship_type=relationship_type,
                properties=properties
            )
            record = await result.single()
            return record is not None
    
    async def find_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find entities related to a given entity"""
        
        # Build relationship type filter
        rel_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"
        
        query = f"""
        MATCH (start {{id: $entity_id}})
        MATCH (start)-[r{rel_filter}*1..{max_depth}]-(related)
        WHERE start <> related
        RETURN DISTINCT related, 
               [rel in r | {{type: rel.type, properties: properties(rel)}}] as relationships
        LIMIT $limit
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                limit=limit
            )
            
            entities = []
            async for record in result:
                entity = dict(record["related"])
                entity["relationships"] = record["relationships"]
                entities.append(entity)
            
            return entities
    
    async def search_entities(
        self,
        query_text: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search entities by text"""
        
        # Build entity type filter
        type_filter = ""
        if entity_types:
            type_labels = "|".join(entity_types)
            type_filter = f":{type_labels}"
        
        # Use full-text search if available, otherwise use CONTAINS
        search_query = f"""
        MATCH (e{type_filter})
        WHERE e.name CONTAINS $query_text 
           OR e.description CONTAINS $query_text
           OR e.title CONTAINS $query_text
        RETURN e, labels(e) as types
        ORDER BY 
            CASE 
                WHEN e.name CONTAINS $query_text THEN 1
                WHEN e.title CONTAINS $query_text THEN 2
                ELSE 3
            END
        LIMIT $limit
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(
                search_query,
                query_text=query_text,
                limit=limit
            )
            
            entities = []
            async for record in result:
                entity = dict(record["e"])
                entity["types"] = record["types"]
                entities.append(entity)
            
            return entities
    
    async def get_entity_context(
        self,
        entity_id: str,
        context_depth: int = 2
    ) -> Dict[str, Any]:
        """Get comprehensive context for an entity"""
        
        query = """
        MATCH (entity {id: $entity_id})
        OPTIONAL MATCH (entity)-[r1]-(connected1)
        OPTIONAL MATCH (connected1)-[r2]-(connected2)
        WHERE connected2 <> entity
        RETURN entity,
               collect(DISTINCT {
                   node: connected1,
                   relationship: r1,
                   depth: 1
               }) + collect(DISTINCT {
                   node: connected2,
                   relationship: r2,
                   depth: 2
               }) as context
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, entity_id=entity_id)
            record = await result.single()
            
            if not record:
                return {}
            
            entity = dict(record["entity"])
            context_items = record["context"]
            
            return {
                "entity": entity,
                "connected_entities": [
                    {
                        "entity": dict(item["node"]) if item["node"] else None,
                        "relationship": dict(item["relationship"]) if item["relationship"] else None,
                        "depth": item["depth"]
                    }
                    for item in context_items
                    if item["node"] is not None
                ]
            }
    
    async def find_path_between_entities(
        self,
        start_id: str,
        end_id: str,
        max_length: int = 5
    ) -> List[Dict[str, Any]]:
        """Find shortest path between two entities"""
        
        query = """
        MATCH (start {id: $start_id}), (end {id: $end_id})
        MATCH path = shortestPath((start)-[*1..{max_length}]-(end))
        RETURN [node in nodes(path) | properties(node)] as nodes,
               [rel in relationships(path) | {type: rel.type, properties: properties(rel)}] as relationships
        """.format(max_length=max_length)
        
        async with get_neo4j_session() as session:
            result = await session.run(
                query,
                start_id=start_id,
                end_id=end_id
            )
            
            paths = []
            async for record in result:
                paths.append({
                    "nodes": record["nodes"],
                    "relationships": record["relationships"],
                    "length": len(record["nodes"]) - 1
                })
            
            return paths
    
    async def get_entity_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        
        queries = {
            "total_entities": "MATCH (n) RETURN count(n) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "entity_types": """
                MATCH (n) 
                RETURN labels(n) as types, count(n) as count 
                ORDER BY count DESC
            """,
            "relationship_types": """
                MATCH ()-[r]->() 
                RETURN r.type as type, count(r) as count 
                ORDER BY count DESC
            """,
        }
        
        stats = {}
        
        async with get_neo4j_session() as session:
            for stat_name, query in queries.items():
                try:
                    result = await session.run(query)
                    if stat_name in ["total_entities", "total_relationships"]:
                        record = await result.single()
                        stats[stat_name] = record["count"] if record else 0
                    else:
                        records = [dict(record) async for record in result]
                        stats[stat_name] = records
                except Exception as e:
                    logger.error(f"Failed to get {stat_name}", error=str(e))
                    stats[stat_name] = 0 if "total" in stat_name else []
        
        return stats
    
    async def semantic_search(
        self,
        query_embedding: List[float],
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings"""
        
        # Note: This requires Neo4j with vector similarity capabilities
        # For now, we'll use a placeholder that combines text search with graph traversal
        
        # Extract keywords from query for text search
        # This is a simplified approach - in production, you'd use proper NLP
        
        type_filter = ""
        if entity_types:
            type_labels = "|".join(entity_types)
            type_filter = f":{type_labels}"
        
        # Placeholder query - would need actual vector similarity in production
        query = f"""
        MATCH (e{type_filter})
        WHERE e.embedding IS NOT NULL
        RETURN e, 
               // Placeholder similarity calculation
               0.8 as similarity_score
        ORDER BY similarity_score DESC
        LIMIT $limit
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, limit=limit)
            
            entities = []
            async for record in result:
                entity = dict(record["e"])
                entity["similarity_score"] = record["similarity_score"]
                entities.append(entity)
            
            return entities
    
    async def build_citation_graph(self, citations: List[Citation]) -> Dict[str, Any]:
        """Build a subgraph showing relationships between citations"""
        
        citation_ids = [citation.id for citation in citations]
        
        query = """
        MATCH (c1:Citation), (c2:Citation)
        WHERE c1.id IN $citation_ids AND c2.id IN $citation_ids
        OPTIONAL MATCH (c1)-[r]-(c2)
        RETURN c1, c2, r
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, citation_ids=citation_ids)
            
            nodes = {}
            edges = []
            
            async for record in result:
                # Add nodes
                for node_key in ["c1", "c2"]:
                    if record[node_key]:
                        node = dict(record[node_key])
                        nodes[node["id"]] = node
                
                # Add relationship
                if record["r"]:
                    rel = dict(record["r"])
                    edges.append({
                        "from": record["c1"]["id"],
                        "to": record["c2"]["id"],
                        "type": rel.get("type", "RELATED"),
                        "properties": {k: v for k, v in rel.items() if k != "type"}
                    })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }