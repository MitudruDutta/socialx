from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
from collections import defaultdict
from loguru import logger
from app.config import settings
from app.api.v1.router import api_router
from app.storage import init_db
import sentry_sdk
import time
from functools import lru_cache

# Simple API key auth
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key for protected endpoints"""
    if settings.ENVIRONMENT == "development" and settings.DEBUG:
        return True  # Skip auth in dev mode
    
    if not api_key or api_key != settings.SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# Singleton accessor for ImageGenerator to ensure we can unload the correct instance
@lru_cache(maxsize=1)
def get_image_generator():
    from app.generators.image_generator import ImageGenerator
    return ImageGenerator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Twitter AI Agent...")
    
    # Initialize DB tables
    try:
        init_db()
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT
        )
        logger.info("Sentry initialized.")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")
    
    # Cleanup image generator GPU memory
    try:
        gen = get_image_generator()
        gen.unload_model()
    except Exception as e:
        logger.warning(f"Failed to unload model: {e}")


app = FastAPI(
    title="Twitter AI Agent",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url=None
)

# CORS - Restrict in production, handle wildcards safely
allowed_origins = ["*"] if settings.DEBUG else [
    "http://localhost:3000",
    "http://localhost:8000",
]

# If wildcard is used, we cannot allow credentials
allow_credentials = True
if "*" in allowed_origins:
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Rate limiting middleware (simple in-memory)
request_counts = defaultdict(list)
RATE_LIMIT = 60  # requests per minute
RATE_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.DEBUG:
        return await call_next(request)
    
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] 
        if now - t < RATE_WINDOW
    ]
    
    # Remove empty entries to prevent memory leak
    if not request_counts[client_ip]:
        del request_counts[client_ip]
        # Re-accessing effectively creates empty list if we needed to append, 
        # but here we check length first.
        # Wait, if we deleted it, checking len below will recreate it empty.
    
    current_count = len(request_counts.get(client_ip, []))
    
    if current_count >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # This will recreate the key if we deleted it, which is fine as we are adding a new request
    request_counts[client_ip].append(now)
    return await call_next(request)


# Include routers with auth dependency
app.include_router(
    api_router, 
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)]
)


@app.get("/")
async def root():
    return {
        "status": "running", 
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health():
    """Public health endpoint (no auth required)"""
    from app.monitoring.health_checker import HealthChecker
    
    checker = HealthChecker()
    try:
        return await checker.run_all_checks()
    finally:
        await checker.close()


@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "pong"}
