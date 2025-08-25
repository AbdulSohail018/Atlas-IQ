"""
RAG (Retrieval-Augmented Generation) Service
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import numpy as np
from datetime import datetime
import structlog

from app.core.database import get_vector_session, get_neo4j_session, get_duckdb_connection
from app.services.llm_service import LLMService
from app.services.knowledge_graph import KnowledgeGraphService
from app.core.config import settings

logger = structlog.get_logger()


class RAGService:
    """Service for retrieval-augmented generation"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.kg_service = KnowledgeGraphService()
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 10,
        include_graph_context: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context using hybrid retrieval (vector + graph + keyword)
        """
        
        # Generate query embedding
        try:
            query_embeddings = await self.llm_service.generate_embeddings([query])
            query_embedding = query_embeddings[0]
        except Exception as e:
            logger.warning("Failed to generate query embedding", error=str(e))
            query_embedding = None
        
        # Parallel retrieval from different sources
        retrieval_tasks = [
            self._vector_search(query_embedding, top_k) if query_embedding else asyncio.create_task(self._empty_result()),
            self._keyword_search(query, top_k),
            self._graph_search(query, top_k) if include_graph_context else asyncio.create_task(self._empty_result())
        ]
        
        vector_results, keyword_results, graph_results = await asyncio.gather(*retrieval_tasks)
        
        # Combine and re-rank results
        combined_results = self._combine_and_rerank(
            vector_results, keyword_results, graph_results, query, top_k
        )
        
        # Apply filters if provided
        if filters:
            combined_results = self._apply_filters(combined_results, filters)
        
        # Ensure context doesn't exceed max length
        final_results = self._truncate_context(combined_results)
        
        logger.info(
            "Context retrieval completed",
            query_length=len(query),
            vector_results=len(vector_results),
            keyword_results=len(keyword_results),
            graph_results=len(graph_results),
            final_results=len(final_results)
        )
        
        return final_results
    
    async def _empty_result(self) -> List[Dict[str, Any]]:
        """Return empty result for disabled retrieval methods"""
        return []
    
    async def _vector_search(
        self, 
        query_embedding: List[float], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        
        if not query_embedding:
            return []
        
        try:
            # SQL query for pgvector similarity search
            query = """
            SELECT 
                id,
                content,
                metadata,
                title,
                source,
                document_type,
                embedding <-> %s as distance
            FROM document_embeddings
            WHERE embedding <-> %s < %s
            ORDER BY embedding <-> %s
            LIMIT %s
            """
            
            async with get_vector_session() as session:
                result = await session.execute(
                    query,
                    (query_embedding, query_embedding, 1.0 - self.similarity_threshold, query_embedding, top_k)
                )
                
                rows = result.fetchall()
                
                documents = []
                for row in rows:
                    documents.append({
                        "id": row.id,
                        "content": row.content,
                        "title": row.title,
                        "source": row.source,
                        "document_type": row.document_type,
                        "metadata": row.metadata or {},
                        "score": 1.0 - row.distance,  # Convert distance to similarity
                        "retrieval_method": "vector"
                    })
                
                return documents
        
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            return []
    
    async def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search using DuckDB"""
        
        try:
            # Extract keywords and build search query
            keywords = self._extract_keywords(query)
            keyword_query = " OR ".join([f"content ILIKE '%{kw}%'" for kw in keywords])
            
            # DuckDB full-text search
            search_query = f"""
            SELECT 
                id,
                title,
                content,
                source,
                document_type,
                metadata,
                -- Simple scoring based on keyword matches
                (
                    {" + ".join([f"(CASE WHEN content ILIKE '%{kw}%' THEN 1 ELSE 0 END)" for kw in keywords])}
                ) / {len(keywords)} as score
            FROM documents
            WHERE {keyword_query}
            ORDER BY score DESC
            LIMIT {top_k}
            """
            
            duckdb_conn = get_duckdb_connection()
            result = duckdb_conn.execute(search_query).fetchall()
            
            documents = []
            for row in result:
                documents.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "source": row[3],
                    "document_type": row[4],
                    "metadata": row[5] or {},
                    "score": float(row[6]),
                    "retrieval_method": "keyword"
                })
            
            return documents
        
        except Exception as e:
            logger.error("Keyword search failed", error=str(e))
            return []
    
    async def _graph_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform graph-based search"""
        
        try:
            # Find entities related to query
            entities = await self.kg_service.search_entities(
                query_text=query,
                limit=5
            )
            
            if not entities:
                return []
            
            # Get context for found entities
            context_documents = []
            
            for entity in entities[:3]:  # Limit to top 3 entities
                entity_context = await self.kg_service.get_entity_context(
                    entity_id=entity["id"],
                    context_depth=2
                )
                
                # Convert entity context to document format
                if entity_context:
                    content = f"Entity: {entity.get('name', 'Unknown')}\n"
                    content += f"Description: {entity.get('description', 'No description')}\n"
                    
                    for connected in entity_context.get("connected_entities", []):
                        if connected["entity"]:
                            content += f"Related: {connected['entity'].get('name', 'Unknown')} "
                            content += f"({connected.get('relationship', {}).get('type', 'RELATED')})\n"
                    
                    context_documents.append({
                        "id": f"entity_{entity['id']}",
                        "title": entity.get("name", "Entity"),
                        "content": content,
                        "source": "Knowledge Graph",
                        "document_type": "entity",
                        "metadata": {
                            "entity_types": entity.get("types", []),
                            "entity_id": entity["id"]
                        },
                        "score": 0.8,  # Default graph score
                        "retrieval_method": "graph"
                    })
            
            return context_documents[:top_k]
        
        except Exception as e:
            logger.error("Graph search failed", error=str(e))
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query (simplified)"""
        
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "of", "with", "by", "is", "are", "was", "were", "what", "how", "why",
            "when", "where", "who", "which"
        }
        
        # Simple tokenization and filtering
        words = query.lower().split()
        keywords = [word.strip(".,!?;:") for word in words 
                   if word.strip(".,!?;:") not in stop_words and len(word) > 2]
        
        return keywords[:10]  # Limit to 10 keywords
    
    def _combine_and_rerank(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Combine results from different retrieval methods and rerank"""
        
        # Create a document index to avoid duplicates
        doc_index = {}
        
        # Weight for different retrieval methods
        weights = {
            "vector": 0.5,
            "keyword": 0.3,
            "graph": 0.2
        }
        
        # Add vector results
        for doc in vector_results:
            doc_id = doc["id"]
            if doc_id not in doc_index:
                doc_index[doc_id] = doc.copy()
                doc_index[doc_id]["combined_score"] = doc["score"] * weights["vector"]
                doc_index[doc_id]["retrieval_methods"] = ["vector"]
            else:
                # Boost score for documents found by multiple methods
                doc_index[doc_id]["combined_score"] += doc["score"] * weights["vector"]
                doc_index[doc_id]["retrieval_methods"].append("vector")
        
        # Add keyword results
        for doc in keyword_results:
            doc_id = doc["id"]
            if doc_id not in doc_index:
                doc_index[doc_id] = doc.copy()
                doc_index[doc_id]["combined_score"] = doc["score"] * weights["keyword"]
                doc_index[doc_id]["retrieval_methods"] = ["keyword"]
            else:
                doc_index[doc_id]["combined_score"] += doc["score"] * weights["keyword"]
                doc_index[doc_id]["retrieval_methods"].append("keyword")
        
        # Add graph results
        for doc in graph_results:
            doc_id = doc["id"]
            if doc_id not in doc_index:
                doc_index[doc_id] = doc.copy()
                doc_index[doc_id]["combined_score"] = doc["score"] * weights["graph"]
                doc_index[doc_id]["retrieval_methods"] = ["graph"]
            else:
                doc_index[doc_id]["combined_score"] += doc["score"] * weights["graph"]
                doc_index[doc_id]["retrieval_methods"].append("graph")
        
        # Sort by combined score
        combined_results = sorted(
            doc_index.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return combined_results[:top_k]
    
    def _apply_filters(
        self, 
        results: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to search results"""
        
        filtered_results = []
        
        for result in results:
            include = True
            
            # Date range filter
            if "date_range" in filters:
                # Implementation would depend on metadata structure
                pass
            
            # Source filter
            if "sources" in filters and filters["sources"]:
                if result.get("source") not in filters["sources"]:
                    include = False
            
            # Document type filter
            if "data_type" in filters and filters["data_type"]:
                if isinstance(filters["data_type"], dict):
                    # MongoDB-style query
                    if "$in" in filters["data_type"]:
                        if result.get("document_type") not in filters["data_type"]["$in"]:
                            include = False
                elif result.get("document_type") != filters["data_type"]:
                    include = False
            
            # Dataset ID filter
            if "dataset_id" in filters and filters["dataset_id"]:
                if isinstance(filters["dataset_id"], dict):
                    if "$in" in filters["dataset_id"]:
                        dataset_id = result.get("metadata", {}).get("dataset_id")
                        if dataset_id not in filters["dataset_id"]["$in"]:
                            include = False
            
            if include:
                filtered_results.append(result)
        
        return filtered_results
    
    def _truncate_context(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Truncate context to fit within max context length"""
        
        total_length = 0
        truncated_results = []
        
        for result in results:
            content_length = len(result["content"])
            
            if total_length + content_length <= self.max_context_length:
                truncated_results.append(result)
                total_length += content_length
            else:
                # Truncate the content to fit
                remaining_length = self.max_context_length - total_length
                if remaining_length > 100:  # Only include if meaningful content can fit
                    truncated_result = result.copy()
                    truncated_result["content"] = result["content"][:remaining_length] + "..."
                    truncated_results.append(truncated_result)
                break
        
        return truncated_results
    
    async def index_document(
        self,
        document_id: str,
        title: str,
        content: str,
        source: str,
        document_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Index a document for retrieval"""
        
        try:
            # Generate embeddings
            embeddings = await self.llm_service.generate_embeddings([content])
            embedding = embeddings[0]
            
            # Store in vector database
            insert_query = """
            INSERT INTO document_embeddings 
            (id, title, content, source, document_type, metadata, embedding, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                source = EXCLUDED.source,
                document_type = EXCLUDED.document_type,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                updated_at = %s
            """
            
            async with get_vector_session() as session:
                await session.execute(
                    insert_query,
                    (
                        document_id, title, content, source, document_type,
                        metadata or {}, embedding, datetime.utcnow(), datetime.utcnow()
                    )
                )
                await session.commit()
            
            # Also store in DuckDB for keyword search
            duckdb_conn = get_duckdb_connection()
            duckdb_conn.execute("""
                INSERT OR REPLACE INTO documents 
                (id, title, content, source, document_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (document_id, title, content, source, document_type, 
                  str(metadata or {}), datetime.utcnow().isoformat()))
            
            logger.info("Document indexed successfully", document_id=document_id)
            return True
        
        except Exception as e:
            logger.error("Failed to index document", document_id=document_id, error=str(e))
            return False
    
    async def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval system statistics"""
        
        try:
            # Vector database stats
            async with get_vector_session() as session:
                vector_result = await session.execute(
                    "SELECT COUNT(*) as count FROM document_embeddings"
                )
                vector_count = vector_result.scalar()
            
            # DuckDB stats
            duckdb_conn = get_duckdb_connection()
            keyword_result = duckdb_conn.execute(
                "SELECT COUNT(*) as count FROM documents"
            ).fetchone()
            keyword_count = keyword_result[0] if keyword_result else 0
            
            # Knowledge graph stats
            kg_stats = await self.kg_service.get_entity_statistics()
            
            return {
                "vector_documents": vector_count,
                "keyword_documents": keyword_count,
                "graph_entities": kg_stats.get("total_entities", 0),
                "graph_relationships": kg_stats.get("total_relationships", 0),
                "last_updated": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error("Failed to get retrieval stats", error=str(e))
            return {
                "error": "Failed to retrieve statistics",
                "timestamp": datetime.utcnow().isoformat()
            }