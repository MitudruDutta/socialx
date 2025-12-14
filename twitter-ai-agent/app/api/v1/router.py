from fastapi import APIRouter
from app.api.v1.endpoints import tweets, health

api_router = APIRouter()
api_router.include_router(tweets.router, prefix="/tweets", tags=["tweets"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
