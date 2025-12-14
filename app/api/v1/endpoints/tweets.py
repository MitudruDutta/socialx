from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.agents.orchestrator import TwitterAgentOrchestrator
from app.generators.text_generator import TextGenerator

router = APIRouter()

class TweetRequest(BaseModel):
    content: Optional[str] = None
    topic: Optional[str] = None
    with_image: bool = False

class GenerateRequest(BaseModel):
    topic: str
    tone: Optional[str] = None

@router.post("/generate")
async def generate_tweet(request: GenerateRequest):
    gen = TextGenerator()
    tweet = await gen.generate_tweet(topic=request.topic, tone=request.tone)
    return {"tweet": tweet}

@router.post("/create")
async def create_content(request: TweetRequest):
    if not request.topic:
        raise HTTPException(400, "Topic required")
    
    orchestrator = TwitterAgentOrchestrator()
    content = await orchestrator.create_content(
        topic=request.topic,
        with_image=request.with_image
    )
    return content

@router.get("/mentions")
async def get_mentions():
    from app.automation.playwright_bot import PlaywrightTwitterBot
    
    async with PlaywrightTwitterBot() as bot:
        await bot.login()
        mentions = await bot.get_mentions(limit=20)
    
    return {"mentions": mentions}

@router.post("/run-workflow")
async def run_workflow():
    orchestrator = TwitterAgentOrchestrator()
    result = await orchestrator.run()
    return result
