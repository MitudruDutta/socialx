from typing import Dict, Any
from datetime import datetime, timezone
from loguru import logger
from app.config import settings
from sqlalchemy import text, create_engine
import psutil
import redis.asyncio as redis
import asyncio

BYTES_PER_GB = 1024**3

class HealthChecker:
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        try:
            redis_kwargs = {}
            if settings.REDIS_URL.startswith("rediss://"):
                if settings.ENVIRONMENT == "development":
                    redis_kwargs["ssl_cert_reqs"] = None
            
            self.redis_client = redis.from_url(settings.REDIS_URL, **redis_kwargs)
        except Exception as e:
            logger.warning(f"Failed to init Redis client: {e}")
            self.redis_client = None
    
    async def close(self):
        """Cleanup resources - MUST be called after use"""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception:
                pass
            self.redis_client = None

    async def run_all_checks(self) -> Dict[str, Any]:
        logger.info("Running health checks...")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        checks = [
            ("database", self._check_database),
            ("redis", self._check_redis),
            ("disk", self._check_disk),
            ("memory", self._check_memory),
            ("llm", self._check_llm),
        ]
        
        for name, check in checks:
            try:
                results["checks"][name] = await check()
                if not results["checks"][name].get("healthy", False):
                    results["overall_status"] = "unhealthy"
            except Exception as e:
                results["checks"][name] = {"healthy": False, "error": str(e)}
                results["overall_status"] = "unhealthy"
        
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        engine = None
        try:
            engine = create_engine(settings.DATABASE_URL)
            await asyncio.to_thread(self._run_sync_db_check, engine)
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
        finally:
            if engine:
                engine.dispose()

    def _run_sync_db_check(self, engine):
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    
    async def _check_redis(self) -> Dict[str, Any]:
        if not self.redis_client:
            return {"healthy": False, "error": "Redis client not initialized"}
        
        try:
            await self.redis_client.ping()
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_disk(self) -> Dict[str, Any]:
        try:
            disk = await asyncio.to_thread(psutil.disk_usage, '/')
            healthy = disk.percent < 90
            return {
                "healthy": healthy,
                "percent_used": disk.percent,
                "free_gb": round(disk.free / BYTES_PER_GB, 2),
                "warning": "Low disk space" if not healthy else None
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_memory(self) -> Dict[str, Any]:
        try:
            memory = await asyncio.to_thread(psutil.virtual_memory)
            healthy = memory.percent < 90
            return {
                "healthy": healthy,
                "percent_used": memory.percent,
                "available_gb": round(memory.available / BYTES_PER_GB, 2),
                "warning": "High memory usage" if not healthy else None
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _check_llm(self) -> Dict[str, Any]:
        """Check if at least one LLM is available"""
        available = []
        
        if settings.OPENAI_API_KEY:
            available.append("openai")
        if settings.GOOGLE_API_KEY:
            available.append("gemini")
        
        # Check Ollama
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    available.append("ollama")
        except Exception:
            pass
        
        return {
            "healthy": len(available) > 0,
            "available_providers": available,
            "warning": "No LLM available" if not available else None
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
