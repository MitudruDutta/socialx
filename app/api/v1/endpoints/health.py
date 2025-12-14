from fastapi import APIRouter
from app.monitoring.health_checker import HealthChecker

router = APIRouter()

@router.get("/")
async def health_check():
    checker = HealthChecker()
    return await checker.run_all_checks()

@router.get("/ping")
async def ping():
    return {"status": "pong"}
