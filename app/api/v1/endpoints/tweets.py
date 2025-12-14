from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.agents.orchestrator import TwitterAgentOrchestrator
from app.generators.text_generator import TextGenerator
from loguru import logger

router = APIRouter()


class TweetRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    with_image: bool = False


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    tone: Optional[str] = Field(None, max_length=50)


class WorkflowResponse(BaseModel):
    status: str
    mentions_count: int = 0
    responses_count: int = 0
    errors_count: int = 0
    errors: List[str] = []


class PostResponse(BaseModel):
    posted: bool
    text: str
    status: str


@router.post("/generate", response_model=Dict[str, str])
async def generate_tweet(request: GenerateRequest):
    """Generate tweet text without posting"""
    try:
        gen = TextGenerator()
        tweet = await gen.generate_tweet(topic=request.topic, tone=request.tone)
        return {"tweet": tweet, "length": str(len(tweet))}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tweet generation failed: {e}")
        raise HTTPException(status_code=500, detail="Generation failed")


@router.post("/create", response_model=Dict[str, Any])
async def create_content(request: TweetRequest):
    """Generate content (text + optional image) without posting"""
    try:
        orchestrator = TwitterAgentOrchestrator()
        content = await orchestrator.create_content(
            topic=request.topic,
            with_image=request.with_image
        )
        return {
            "text": content["text"],
            "media": content.get("media", []),
            "length": len(content["text"])
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Content creation failed: {e}")
        raise HTTPException(status_code=500, detail="Content creation failed")


@router.get("/mentions")
async def get_mentions(limit: int = 20):
    """Fetch recent mentions from Twitter"""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    try:
        from app.automation.playwright_bot import PlaywrightTwitterBot
        
        async with PlaywrightTwitterBot() as bot:
            await bot.login()
            mentions = await bot.get_mentions(limit=limit)
        
        return {"mentions": mentions, "count": len(mentions)}
    except Exception as e:
        logger.error(f"Failed to fetch mentions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mentions")


@router.post("/run-workflow", response_model=WorkflowResponse)
async def run_workflow():
    """Run the full mention-check and response workflow"""
    try:
        orchestrator = TwitterAgentOrchestrator()
        result = await orchestrator.run()
        
        return WorkflowResponse(
            status="completed" if not result.get("failed") else "failed",
            mentions_count=len(result.get("mentions", [])),
            responses_count=len(result.get("responses", [])),
            errors_count=len(result.get("errors", [])),
            errors=result.get("errors", [])[:5]  # Return first 5 errors
        )
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")


@router.post("/post", response_model=PostResponse)
async def post_content(request: TweetRequest):
    """Generate and post content to Twitter"""
    try:
        orchestrator = TwitterAgentOrchestrator()
        
        # Generate
        content = await orchestrator.create_content(
            topic=request.topic,
            with_image=request.with_image
        )
        
        # Post
        success = await orchestrator.post_content(content)
        
        return PostResponse(
            posted=success,
            text=content["text"],
            status="posted" if success else "saved_as_draft"
        )
    except Exception as e:
        logger.error(f"Post failed: {e}")
        raise HTTPException(status_code=500, detail="Content posting failed")
