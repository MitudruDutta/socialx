from typing import TypedDict, List, Dict, Any, Annotated
import operator
import asyncio
import random
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from app.config import settings
from app.generators.text_generator import TextGenerator
from app.generators.image_generator import ImageGenerator
from app.automation.playwright_bot import PlaywrightTwitterBot
from app.storage import SessionLocal
from app.storage.models import Mention, Tweet, Action, TweetStatus, ActionType

class AgentState(TypedDict):
    mentions: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    content: List[Dict[str, Any]]
    errors: Annotated[List[str], operator.add]

class TwitterAgentOrchestrator:
    def __init__(self):
        self.text_gen = TextGenerator()
        self.image_gen = ImageGenerator()
    
    async def run(self) -> Dict[str, Any]:
        logger.info("🤖 Starting agent workflow...")
        
        state: AgentState = {
            "mentions": [],
            "responses": [],
            "content": [],
            "errors": []
        }
        
        try:
            # Step 1: Fetch mentions
            state = await self._listen(state)
            
            # Step 2: Generate responses
            state = await self._respond(state)
            
            # Step 3: Execute actions
            state = await self._execute(state)
            
            logger.success("✅ Workflow completed")
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            state["errors"].append(str(e))
        
        return state
    
    async def _listen(self, state: AgentState) -> AgentState:
        logger.info("🎧 Fetching mentions...")
        
        try:
            async with PlaywrightTwitterBot() as bot:
                await bot.login()
                raw_mentions = await bot.get_mentions(limit=10)
            
            with SessionLocal() as db:
                new_mentions = []
                for m in raw_mentions:
                    # Check if exists
                    exists = db.query(Mention).filter(Mention.twitter_id == m["tweet_id"]).first()
                    if not exists:
                        # Save to DB
                        db_mention = Mention(
                            twitter_id=m["tweet_id"],
                            author_username=m["username"],
                            content=m["text"],
                            mentioned_at=datetime.utcnow(),  # Approximate
                            processed=False
                        )
                        db.add(db_mention)
                        new_mentions.append(m)
                
                db.commit()
                state["mentions"] = new_mentions
                logger.success(f"Found {len(new_mentions)} new mentions (filtered from {len(raw_mentions)})")

        except Exception as e:
            logger.error(f"Listen failed: {e}")
            state["errors"].append(f"Listen: {e}")
        
        return state
    
    async def _respond(self, state: AgentState) -> AgentState:
        logger.info("💬 Generating responses...")
        
        with SessionLocal() as db:
            for mention in state["mentions"]:
                try:
                    response_text = await self.text_gen.generate_reply(
                        original_tweet=mention["text"],
                        author=mention["username"]
                    )
                    
                    # Save Draft Response
                    db_tweet = Tweet(
                        content=response_text,
                        status=TweetStatus.DRAFT,
                        # Link to mention logic could be added here if model supported it directly,
                        # for now we track flow in state
                    )
                    db.add(db_tweet)
                    db.commit()
                    db.refresh(db_tweet)

                    state["responses"].append({
                        "mention_url": mention["url"],
                        "response_text": response_text,
                        "username": mention["username"],
                        "db_tweet_id": db_tweet.id,
                        "mention_db_id": mention.get("tweet_id") # strictly it's the twitter ID
                    })
                except Exception as e:
                    state["errors"].append(f"Response gen: {e}")
        
        logger.success(f"Generated {len(state['responses'])} responses")
        return state
    
    async def _execute(self, state: AgentState) -> AgentState:
        logger.info("🚀 Executing actions...")
        
        if settings.REQUIRE_HUMAN_REVIEW:
            logger.info("Human review required - skipping auto-post")
            return state
        
        try:
            async with PlaywrightTwitterBot() as bot:
                await bot.login()
                
                with SessionLocal() as db:
                    for response in state["responses"]:
                        try:
                            await bot.post_tweet(
                                content=response["response_text"],
                                reply_to_url=response["mention_url"]
                            )
                            
                            # Update DB
                            if "db_tweet_id" in response:
                                db_tweet = db.query(Tweet).filter(Tweet.id == response["db_tweet_id"]).first()
                                if db_tweet:
                                    db_tweet.status = TweetStatus.POSTED
                                    db_tweet.posted_at = datetime.utcnow()
                            
                            # Mark mention as processed
                            # (We'd need to fetch the specific mention row, but we used twitter_id)
                            if "mention_db_id" in response:
                                db_mention = db.query(Mention).filter(Mention.twitter_id == response["mention_db_id"]).first()
                                if db_mention:
                                    db_mention.responded = True
                                    db_mention.processed = True

                            await asyncio.sleep(random.uniform(
                                settings.MIN_ACTION_DELAY,
                                settings.MAX_ACTION_DELAY
                            ))
                        except Exception as e:
                            logger.error(f"Failed to reply to {response['username']}: {e}")
                            state["errors"].append(f"Reply error: {e}")
                    db.commit()

        except Exception as e:
            state["errors"].append(f"Execute: {e}")
        
        return state
    
    async def create_content(self, topic: str, with_image: bool = False) -> Dict[str, Any]:
        """Generate original content for posting"""
        logger.info(f"Creating content about: {topic}")
        
        tweet_text = await self.text_gen.generate_tweet(topic=topic)
        
        result = {"text": tweet_text, "media": []}
        
        if with_image and settings.ENABLE_IMAGE_GENERATION:
            image_path = await self.image_gen.generate(prompt=topic)
            result["media"].append(image_path)
        
        return result

    async def post_content(self, content: Dict[str, Any]) -> bool:
        """Post generated content to Twitter"""
        if settings.REQUIRE_HUMAN_REVIEW:
            logger.info("Human review required - skipping auto-post of new content")
            return False

        logger.info("🚀 Posting new content...")
        try:
            async with PlaywrightTwitterBot() as bot:
                await bot.login()
                await bot.post_tweet(
                    content=content["text"],
                    media_paths=content["media"]
                )
            
            # Save to DB
            with SessionLocal() as db:
                db_tweet = Tweet(
                    content=content["text"],
                    status=TweetStatus.POSTED,
                    posted_at=datetime.utcnow(),
                    has_image=bool(content["media"]),
                    media_urls=content["media"]
                )
                db.add(db_tweet)
                db.commit()

            logger.success("✅ Content posted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to post content: {e}")
            return False
