from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from app.config import settings
from app.api.v1.router import api_router
from app.storage import init_db
import sentry_sdk

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Twitter AI Agent...")
    
    # Initialize DB tables
    try:
        init_db()
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            send_default_pii=True,
            enable_logs=True,
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
            profile_lifecycle="trace",
        )
        logger.info("Sentry initialized.")
    else:
        logger.warning("SENTRY_DSN not set, Sentry monitoring disabled.")
    
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="Twitter AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    from app.monitoring.health_checker import HealthChecker
    checker = HealthChecker()
    return await checker.run_all_checks()
