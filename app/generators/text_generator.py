from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import settings
import httpx


class TextGenerator:
    def __init__(self):
        self.primary_llm = None
        self.fallback_llm = None
        self._init_models()
    
    def _init_models(self):
        if settings.OPENAI_API_KEY:
            try:
                self.primary_llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    temperature=settings.OPENAI_TEMPERATURE,
                    request_timeout=30
                )
                logger.info("Primary LLM (OpenAI) initialized")
            except Exception as e:
                logger.warning(f"Failed to init OpenAI: {e}")
                
        if settings.GOOGLE_API_KEY:
            try:
                self.fallback_llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-pro",
                    google_api_key=settings.GOOGLE_API_KEY
                )
                logger.info("Fallback LLM (Gemini) initialized")
            except Exception as e:
                logger.warning(f"Failed to init Gemini: {e}")
    
    async def generate_tweet(
        self, 
        topic: str, 
        context: Optional[str] = None, 
        tone: Optional[str] = None
    ) -> str:
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")
        
        tone = tone or settings.BRAND_VOICE
        prompt = f"""Write an engaging tweet about: {topic}
{f'Context: {context}' if context else ''}
Tone: {tone}
Requirements: Max 280 chars, authentic, include 1-2 hashtags if appropriate.
Return ONLY the tweet text, no quotes or explanation."""
        
        result = await self._generate(prompt)
        
        if not result or not result.strip():
            raise ValueError("Generated empty tweet")
        
        return result
    
    async def generate_reply(
        self, 
        original_tweet: str, 
        author: str, 
        tone: Optional[str] = None
    ) -> str:
        if not original_tweet or not original_tweet.strip():
            raise ValueError("Original tweet cannot be empty")
        if not author or not author.strip():
            raise ValueError("Author cannot be empty")
        
        tone = tone or settings.BRAND_VOICE
        prompt = f"""Reply to this tweet from @{author}:
"{original_tweet}"
Tone: {tone}
Requirements: Max 280 chars, helpful, authentic, don't be promotional.
Return ONLY the reply text, no quotes or explanation."""
        
        result = await self._generate(prompt)
        
        if not result or not result.strip():
            raise ValueError("Generated empty reply")
        
        return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _generate(self, prompt: str) -> str:
        last_error = None
        
        # Try primary LLM (OpenAI)
        if self.primary_llm:
            try:
                response = await self.primary_llm.ainvoke(prompt)
                result = self._clean(response.content)
                if result:
                    return result
                logger.warning("Primary LLM returned empty response")
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}")
                last_error = e
        
        # Try fallback LLM (Gemini)
        if self.fallback_llm:
            try:
                response = await self.fallback_llm.ainvoke(prompt)
                result = self._clean(response.content)
                if result:
                    return result
                logger.warning("Fallback LLM returned empty response")
            except Exception as e:
                logger.warning(f"Fallback LLM failed: {e}")
                last_error = e
        
        # Try local Ollama
        try:
            result = await self._ollama_generate(prompt)
            if result:
                return result
            logger.warning("Ollama returned empty response")
        except Exception as e:
            logger.error(f"Ollama failed: {e}")
            last_error = e
        
        # All LLMs failed
        error_msg = str(last_error) if last_error else "Empty responses from all providers"
        raise RuntimeError(f"All LLM providers failed. Last error: {error_msg}")
    
    async def _ollama_generate(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL, 
                        "prompt": prompt, 
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return self._clean(data.get("response", ""))
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}")
        except httpx.TimeoutException:
            raise RuntimeError("Ollama request timed out")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")
    
    def _clean(self, text: str) -> str:
        if not text:
            return ""
        
        # Remove quotes, markdown, extra whitespace
        text = text.strip()
        text = text.strip('"\'')
        text = text.replace("**", "").replace("*", "")
        text = text.replace("```", "")
        
        # Remove common LLM prefixes
        prefixes = ["Here's", "Here is", "Tweet:", "Reply:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
                text = text.lstrip(":").strip()
        
        # Truncate to 280 chars
        if len(text) > 280:
            text = text[:277] + "..."
        
        return text
