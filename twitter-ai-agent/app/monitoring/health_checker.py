from typing import Dict, Any
from datetime import datetime, timezone
from loguru import logger
from app.config import settings
from sqlalchemy import text, create_engine
import psutil
import redis.asyncio as redis
import asyncio

class HealthChecker:
    def __init__(self):
        # Configure Redis client
        # Default to safe SSL verification. Only disable if explicitly needed (e.g. for self-signed dev certs)
        # Ideally this should be controlled by a setting like REDIS_SSL_VERIFY_MODE
        redis_kwargs = {}
        if settings.REDIS_URL.startswith("rediss://"):
             # For production, we usually want default verification. 
             # If specific certs are needed, they should be passed via ssl_ca_certs.
             # Here we avoid blindly setting ssl_cert_reqs=None unless we are in a dev environment/explicitly flagged.
             # Assuming 'development' environment might need relaxed checks for local/docker setups:
             if settings.ENVIRONMENT == "development":
                 redis_kwargs["ssl_cert_reqs"] = None
            
        self.redis_client = redis.from_url(settings.REDIS_URL, **redis_kwargs)
    
    async def close(self):
        """Cleanup resources."""
        if self.redis_client:
            await self.redis_client.close()

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
        ]
        
        for name, check in checks:
            try:
                results["checks"][name] = await check()
                if not results["checks"][name]["healthy"]:
                    results["overall_status"] = "unhealthy"
            except Exception as e:
                results["checks"][name] = {"healthy": False, "error": str(e)}
                results["overall_status"] = "unhealthy"
        
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        engine = None
        try:
            # Create a new engine for the check to ensure we test connectivity fresh
            engine = create_engine(settings.DATABASE_URL)
            # Run the synchronous connect/execute in a thread to avoid blocking the loop
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
                "free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
             return {"healthy": False, "percent_used": None, "free_gb": None, "error": str(e)}
    
    async def _check_memory(self) -> Dict[str, Any]:
        try:
            memory = await asyncio.to_thread(psutil.virtual_memory)
            healthy = memory.percent < 90
            return {
                "healthy": healthy,
                "percent_used": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
        except Exception as e:
            return {"healthy": False, "percent_used": None, "available_gb": None, "error": str(e)}
