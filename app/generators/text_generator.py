from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional
from loguru import logger
from app.config import settings
import httpx

class TextGenerator:
    def __init__(self):
        self.primary_llm = None
        self.fallback_llm = None
        self._init_models()
    
    def _init_models(self):
        if settings.OPENAI_API_KEY:
            self.primary_llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE
            )
        if settings.GOOGLE_API_KEY:
            self.fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=settings.GOOGLE_API_KEY
            )
    
    async def generate_tweet(self, topic: str, context: Optional[str] = None, tone: Optional[str] = None) -> str:
        tone = tone or settings.BRAND_VOICE
        prompt = f"""Write an engaging tweet about: {topic}
{f'Context: {context}' if context else ''}
Tone: {tone}
Requirements: Max 280 chars, authentic, include 1-2 hashtags if appropriate.
Return ONLY the tweet text."""
        
        return await self._generate(prompt)
    
    async def generate_reply(self, original_tweet: str, author: str, tone: Optional[str] = None) -> str:
        tone = tone or settings.BRAND_VOICE
        prompt = f"""Reply to this tweet from @{author}:
"{original_tweet}"
Tone: {tone}
Requirements: Max 280 chars, helpful, authentic.
Return ONLY the reply text."""
        
        return await self._generate(prompt)
    
    async def _generate(self, prompt: str) -> str:
        if self.primary_llm:
            try:
                response = await self.primary_llm.ainvoke(prompt)
                return self._clean(response.content)
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}")
        
        if self.fallback_llm:
            try:
                response = await self.fallback_llm.ainvoke(prompt)
                return self._clean(response.content)
            except Exception as e:
                logger.warning(f"Fallback LLM failed: {e}")
        
        return await self._ollama_generate(prompt)
    
    async def _ollama_generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            return self._clean(response.json()["response"])
    
    def _clean(self, text: str) -> str:
        text = text.strip().strip('"\'').replace("**", "")
        return text[:280] if len(text) > 280 else text
