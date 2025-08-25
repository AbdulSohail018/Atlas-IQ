"""
Chat API endpoints
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import structlog
import json
import asyncio

from app.models.chat import (
    ChatRequest, ChatResponse, SimulationRequest, SimulationResponse,
    ConversationHistory, FeedbackRequest, AnalysisRequest, AnalysisResponse,
    QuickQuery, AnswerMode, QueryType
)
from app.models.base import Citation
from app.services.llm_service import LLMService
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.rag_service import RAGService
from app.core.database import get_redis_client

logger = structlog.get_logger()
router = APIRouter()


async def get_llm_service() -> LLMService:
    """Dependency to get LLM service"""
    return LLMService()


async def get_kg_service() -> KnowledgeGraphService:
    """Dependency to get Knowledge Graph service"""
    return KnowledgeGraphService()


async def get_rag_service() -> RAGService:
    """Dependency to get RAG service"""
    return RAGService()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Ask a natural language question and get a grounded answer with citations
    """
    start_time = datetime.utcnow()
    message_id = str(uuid.uuid4())
    
    try:
        # Classify query type
        query_type = llm_service.classify_query_type(request.message)
        
        # Retrieve relevant context using RAG
        context_results = await rag_service.retrieve_context(
            query=request.message,
            top_k=10,
            include_graph_context=True
        )
        
        # Build context string
        context = "\n\n".join([
            f"Source: {result['source']}\nContent: {result['content']}"
            for result in context_results
        ])
        
        # Generate response
        response_content, confidence = await llm_service.generate_response(
            prompt=request.message,
            mode=request.mode,
            context=context if context else None,
            max_tokens=request.max_tokens
        )
        
        # Create citations from context results
        citations = []
        if request.include_citations:
            for i, result in enumerate(context_results[:5]):  # Limit to top 5
                citation = Citation(
                    id=f"cite_{i+1}",
                    title=result.get('title', 'Unknown Document'),
                    source=result.get('source', 'Unknown Source'),
                    excerpt=result['content'][:200] + "..." if len(result['content']) > 200 else result['content'],
                    confidence=result.get('score', 0.8),
                    metadata=result.get('metadata', {})
                )
                citations.append(citation)
        
        # Generate follow-up suggestions
        suggestions = await llm_service.generate_suggestions(
            request.message, response_content
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        response = ChatResponse(
            message_id=message_id,
            content=response_content,
            mode=request.mode,
            query_type=query_type,
            confidence=confidence,
            citations=citations,
            suggestions=suggestions,
            metadata={
                "context_sources": len(context_results),
                "session_id": request.session_id,
                "query_classification": query_type.value
            },
            processing_time=processing_time
        )
        
        # Log query in background
        background_tasks.add_task(
            log_user_query,
            request, response, processing_time
        )
        
        return response
        
    except Exception as e:
        logger.error("Error processing chat request", error=str(e), query=request.message)
        raise HTTPException(status_code=500, detail="Failed to process question")


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_scenario(
    request: SimulationRequest,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Generate forecasts and simulations blending historical data with LLM narratives
    """
    scenario_id = str(uuid.uuid4())
    
    try:
        # Retrieve relevant historical data
        context_results = await rag_service.retrieve_context(
            query=request.scenario,
            top_k=15,
            filters={"data_type": "time_series"}
        )
        
        # Build simulation prompt
        simulation_prompt = f"""
        Scenario: {request.scenario}
        Time Horizon: {request.time_horizon} months
        
        Based on the following historical data and trends, provide a detailed forecast:
        
        {chr(10).join([f"- {result['content'][:300]}" for result in context_results[:10]])}
        
        Please provide:
        1. A narrative describing the likely scenario evolution
        2. Key assumptions underlying the forecast
        3. Major uncertainty factors
        4. Quantitative projections where possible
        """
        
        # Generate simulation response
        narrative, confidence = await llm_service.generate_response(
            prompt=simulation_prompt,
            mode=AnswerMode.ANALYST,
            max_tokens=3000
        )
        
        # Create mock projections (in production, this would use actual forecasting models)
        projections = [
            {
                "time_period": f"Month {i+1}",
                "value": 100 + (i * 2) + (i * 0.1 * hash(request.scenario) % 50),
                "confidence_interval": {
                    "lower": 90 + (i * 1.5),
                    "upper": 110 + (i * 2.5)
                }
            }
            for i in range(min(request.time_horizon, 12))
        ]
        
        # Extract assumptions and uncertainties (simplified)
        assumptions = [
            "Current trends continue linearly",
            "No major disruptive events occur",
            "Policy framework remains stable"
        ]
        
        uncertainty_factors = [
            "Economic volatility",
            "Policy changes",
            "External shocks"
        ]
        
        # Create citations
        citations = []
        for i, result in enumerate(context_results[:3]):
            citation = Citation(
                id=f"sim_cite_{i+1}",
                title=result.get('title', 'Historical Data'),
                source=result.get('source', 'Data Source'),
                excerpt=result['content'][:200] + "...",
                confidence=result.get('score', 0.8),
                metadata=result.get('metadata', {})
            )
            citations.append(citation)
        
        return SimulationResponse(
            scenario_id=scenario_id,
            narrative=narrative,
            projections=projections,
            assumptions=assumptions,
            uncertainty_factors=uncertainty_factors,
            confidence_intervals={
                "overall_confidence": confidence,
                "data_quality": 0.85
            },
            visualizations=[
                {
                    "type": "line_chart",
                    "title": "Projected Trend",
                    "data": projections
                }
            ],
            citations=citations,
            metadata={
                "time_horizon": request.time_horizon,
                "data_sources": len(context_results)
            }
        )
        
    except Exception as e:
        logger.error("Error processing simulation request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate simulation")


@router.get("/suggestions", response_model=List[QuickQuery])
async def get_quick_queries():
    """Get suggested quick queries for common questions"""
    
    quick_queries = [
        QuickQuery(
            id="q1",
            question="What are the air quality trends in major cities?",
            category="Environment",
            description="Analyze air quality data across metropolitan areas",
            suggested_mode=AnswerMode.ANALYST
        ),
        QuickQuery(
            id="q2",
            question="How do climate policies compare between EU and US?",
            category="Policy",
            description="Compare climate legislation and regulations",
            suggested_mode=AnswerMode.RESEARCHER
        ),
        QuickQuery(
            id="q3",
            question="What services can I request through 311 in my area?",
            category="Civic",
            description="Learn about local government services",
            suggested_mode=AnswerMode.CITIZEN
        ),
        QuickQuery(
            id="q4",
            question="How has population demographics changed over the last decade?",
            category="Demographics",
            description="Analyze census and demographic trends",
            suggested_mode=AnswerMode.ANALYST
        ),
        QuickQuery(
            id="q5",
            question="What are the health impacts of urban planning decisions?",
            category="Health",
            description="Explore connections between urban design and public health",
            suggested_mode=AnswerMode.RESEARCHER
        )
    ]
    
    return quick_queries


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback for a chat response"""
    
    try:
        redis_client = await get_redis_client()
        
        # Store feedback in Redis (in production, use proper database)
        feedback_data = {
            "message_id": request.message_id,
            "rating": request.rating,
            "feedback_text": request.feedback_text,
            "helpful_citations": request.helpful_citations,
            "suggested_improvements": request.suggested_improvements,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.set(
            f"feedback:{request.message_id}",
            json.dumps(feedback_data),
            ex=86400 * 30  # 30 days
        )
        
        return {"status": "success", "message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error("Error submitting feedback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""
    
    try:
        redis_client = await get_redis_client()
        
        # Retrieve from Redis (in production, use proper database)
        history_data = await redis_client.get(f"history:{session_id}")
        
        if not history_data:
            return ConversationHistory(
                session_id=session_id,
                messages=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        
        history = json.loads(history_data)
        return ConversationHistory(**history)
        
    except Exception as e:
        logger.error("Error retrieving conversation history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.post("/analyze", response_model=AnalysisResponse)
async def perform_analysis(
    request: AnalysisRequest,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Perform detailed data analysis"""
    
    analysis_id = str(uuid.uuid4())
    
    try:
        # Retrieve relevant data for analysis
        context_results = await rag_service.retrieve_context(
            query=request.query,
            top_k=20,
            filters={"dataset_id": {"$in": request.datasets}}
        )
        
        # Build analysis prompt
        analysis_prompt = f"""
        Perform a detailed {request.analysis_type} analysis to answer: {request.query}
        
        Available data:
        {chr(10).join([f"- {result['content'][:200]}" for result in context_results[:10]])}
        
        Provide:
        1. Executive summary
        2. Key findings with supporting data
        3. Statistical analysis where appropriate
        4. Visualizations recommendations
        5. Actionable recommendations
        6. Analysis limitations
        """
        
        # Generate analysis
        summary, confidence = await llm_service.generate_response(
            prompt=analysis_prompt,
            mode=AnswerMode.ANALYST,
            max_tokens=4000
        )
        
        # Create mock findings and visualizations
        findings = [
            {
                "finding": "Significant correlation found between variables",
                "support": "Statistical analysis shows r=0.73, p<0.001",
                "confidence": 0.9
            },
            {
                "finding": "Trend shows 15% increase over time period",
                "support": "Linear regression analysis of time series data",
                "confidence": 0.85
            }
        ]
        
        visualizations = [
            {
                "type": "scatter_plot",
                "title": "Correlation Analysis",
                "description": "Shows relationship between key variables"
            },
            {
                "type": "time_series",
                "title": "Trend Analysis",
                "description": "Historical trend with projections"
            }
        ]
        
        return AnalysisResponse(
            analysis_id=analysis_id,
            summary=summary,
            findings=findings,
            visualizations=visualizations,
            statistical_summary={
                "sample_size": len(context_results),
                "confidence_level": 0.95,
                "p_value": 0.001
            },
            recommendations=[
                "Continue monitoring trends",
                "Collect additional data points",
                "Implement recommended policies"
            ],
            limitations=[
                "Limited sample size",
                "Potential selection bias",
                "Temporal constraints"
            ],
            citations=[
                Citation(
                    id=f"analysis_cite_{i+1}",
                    title=result.get('title', 'Data Source'),
                    source=result.get('source', 'Unknown'),
                    excerpt=result['content'][:200] + "...",
                    confidence=result.get('score', 0.8)
                )
                for i, result in enumerate(context_results[:5])
            ],
            metadata={
                "analysis_type": request.analysis_type,
                "datasets_used": request.datasets,
                "processing_time": "45.2s"
            }
        )
        
    except Exception as e:
        logger.error("Error performing analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to perform analysis")


async def log_user_query(request: ChatRequest, response: ChatResponse, processing_time: float):
    """Log user query for analytics (background task)"""
    
    try:
        redis_client = await get_redis_client()
        
        query_log = {
            "message_id": response.message_id,
            "query": request.message,
            "mode": request.mode.value,
            "query_type": response.query_type.value if response.query_type else None,
            "confidence": response.confidence,
            "processing_time": processing_time,
            "citations_count": len(response.citations),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": request.session_id
        }
        
        # Store in Redis with TTL
        await redis_client.lpush("query_logs", json.dumps(query_log))
        await redis_client.expire("query_logs", 86400 * 7)  # 7 days
        
        # Update conversation history
        if request.session_id:
            history_key = f"history:{request.session_id}"
            history_data = await redis_client.get(history_key)
            
            if history_data:
                history = json.loads(history_data)
            else:
                history = {
                    "session_id": request.session_id,
                    "messages": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "metadata": {}
                }
            
            # Add messages
            history["messages"].extend([
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "id": response.message_id,
                    "role": "assistant",
                    "content": response.content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "mode": request.mode.value,
                        "confidence": response.confidence,
                        "citations_count": len(response.citations)
                    }
                }
            ])
            
            history["updated_at"] = datetime.utcnow().isoformat()
            
            await redis_client.set(
                history_key,
                json.dumps(history),
                ex=86400 * 7  # 7 days
            )
        
    except Exception as e:
        logger.error("Failed to log query", error=str(e))