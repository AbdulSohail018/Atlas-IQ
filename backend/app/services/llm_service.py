"""
LLM Service for handling language model interactions
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import httpx
import openai
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.chat import AnswerMode, QueryType

logger = structlog.get_logger()


class LLMService:
    """Service for LLM interactions and embedding generation"""
    
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.embedding_model_name = settings.EMBEDDING_MODEL
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Initialized local embedding model")
        except Exception as e:
            logger.warning("Failed to load local embedding model", error=str(e))
            self.embedding_model = None
        
        # Initialize API clients
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
        
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        self.httpx_client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.httpx_client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(
        self,
        prompt: str,
        mode: AnswerMode = AnswerMode.ANALYST,
        context: Optional[str] = None,
        max_tokens: int = 2000
    ) -> Tuple[str, float]:
        """Generate response using available LLM"""
        
        # Build system prompt based on mode
        system_prompt = self._build_system_prompt(mode)
        
        # Add context if provided
        if context:
            prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
        
        # Try Ollama first
        try:
            response, confidence = await self._generate_ollama_response(
                system_prompt, prompt, max_tokens
            )
            return response, confidence
        except Exception as e:
            logger.warning("Ollama request failed, trying fallback", error=str(e))
        
        # Try OpenAI as fallback
        if settings.OPENAI_API_KEY:
            try:
                response, confidence = await self._generate_openai_response(
                    system_prompt, prompt, max_tokens
                )
                return response, confidence
            except Exception as e:
                logger.warning("OpenAI request failed", error=str(e))
        
        # Try Google as last resort
        if settings.GOOGLE_API_KEY:
            try:
                response, confidence = await self._generate_google_response(
                    system_prompt, prompt, max_tokens
                )
                return response, confidence
            except Exception as e:
                logger.error("All LLM providers failed", error=str(e))
        
        raise Exception("No available LLM providers")
    
    async def _generate_ollama_response(
        self, system_prompt: str, prompt: str, max_tokens: int
    ) -> Tuple[str, float]:
        """Generate response using Ollama"""
        
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        response = await self.httpx_client.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        content = result["message"]["content"]
        
        # Estimate confidence based on response length and completeness
        confidence = min(0.9, len(content) / 1000)
        
        return content, confidence
    
    async def _generate_openai_response(
        self, system_prompt: str, prompt: str, max_tokens: int
    ) -> Tuple[str, float]:
        """Generate response using OpenAI"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9
        )
        
        content = response.choices[0].message.content
        
        # OpenAI provides logprobs for confidence estimation
        confidence = 0.85  # Default high confidence for GPT-4
        
        return content, confidence
    
    async def _generate_google_response(
        self, system_prompt: str, prompt: str, max_tokens: int
    ) -> Tuple[str, float]:
        """Generate response using Google Gemini"""
        
        model = genai.GenerativeModel('gemini-pro')
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        response = await model.generate_content_async(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
        )
        
        content = response.text
        confidence = 0.8  # Default confidence for Gemini
        
        return content, confidence
    
    def _build_system_prompt(self, mode: AnswerMode) -> str:
        """Build system prompt based on answer mode"""
        
        base_prompt = """You are Glonav, a Global Policy & Knowledge Navigator assistant that helps users understand public data, policies, and their implications. You have access to diverse datasets including 311 data, climate information, census data, WHO reports, and policy documents.

Always provide accurate, well-sourced answers with proper citations. When referencing data or policies, include specific sources and context."""
        
        if mode == AnswerMode.ANALYST:
            return base_prompt + """

As an ANALYST, you should:
- Provide data-driven insights with statistical analysis
- Include quantitative metrics, trends, and patterns
- Use technical terminology appropriately
- Present findings with charts and visualizations when relevant
- Discuss methodology and limitations
- Compare different data sources and their reliability"""
        
        elif mode == AnswerMode.RESEARCHER:
            return base_prompt + """

As a RESEARCHER, you should:
- Provide comprehensive, academic-style analysis
- Include detailed background and context
- Reference multiple sources and cross-validate information
- Discuss different perspectives and interpretations
- Explain methodologies and data collection approaches
- Suggest areas for further investigation"""
        
        elif mode == AnswerMode.CITIZEN:
            return base_prompt + """

As a CITIZEN advisor, you should:
- Use simple, accessible language
- Focus on practical implications for everyday life
- Explain complex concepts in relatable terms
- Provide actionable information and next steps
- Address common concerns and questions
- Include relevant local resources and contacts"""
        
        return base_prompt
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        
        if self.embedding_model:
            # Use local model
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        
        # Fallback to Ollama embeddings
        try:
            embeddings = []
            for text in texts:
                payload = {
                    "model": self.embedding_model_name,
                    "prompt": text
                }
                
                response = await self.httpx_client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings.append(result["embedding"])
            
            return embeddings
        
        except Exception as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise
    
    def classify_query_type(self, query: str) -> QueryType:
        """Classify query type based on content"""
        
        query_lower = query.lower()
        
        # Policy-related keywords
        policy_keywords = ["policy", "law", "regulation", "legislation", "rule", "mandate", "ordinance"]
        if any(keyword in query_lower for keyword in policy_keywords):
            return QueryType.POLICY
        
        # Data analysis keywords
        analysis_keywords = ["analyze", "trend", "pattern", "correlation", "statistics", "data"]
        if any(keyword in query_lower for keyword in analysis_keywords):
            return QueryType.DATA_ANALYSIS
        
        # Comparison keywords
        comparison_keywords = ["compare", "difference", "versus", "vs", "between", "contrast"]
        if any(keyword in query_lower for keyword in comparison_keywords):
            return QueryType.COMPARISON
        
        # Trend keywords
        trend_keywords = ["trend", "over time", "historical", "change", "increase", "decrease"]
        if any(keyword in query_lower for keyword in trend_keywords):
            return QueryType.TREND
        
        # Simulation keywords
        simulation_keywords = ["predict", "forecast", "what if", "scenario", "projection", "future"]
        if any(keyword in query_lower for keyword in simulation_keywords):
            return QueryType.SIMULATION
        
        return QueryType.GENERAL
    
    async def generate_suggestions(self, query: str, response: str) -> List[str]:
        """Generate follow-up suggestions based on query and response"""
        
        suggestion_prompt = f"""Based on this question and answer, suggest 3 relevant follow-up questions:

Question: {query}
Answer: {response}

Generate 3 concise, specific follow-up questions that would naturally come next. Format as a JSON list of strings."""
        
        try:
            suggestions_text, _ = await self.generate_response(
                suggestion_prompt,
                mode=AnswerMode.ANALYST,
                max_tokens=200
            )
            
            # Try to parse as JSON
            try:
                suggestions = json.loads(suggestions_text)
                if isinstance(suggestions, list):
                    return suggestions[:3]
            except:
                pass
            
            # Fallback: split by lines and clean
            lines = suggestions_text.strip().split('\n')
            suggestions = [line.strip('- ').strip() for line in lines if line.strip()]
            return suggestions[:3]
        
        except Exception as e:
            logger.warning("Failed to generate suggestions", error=str(e))
            return []