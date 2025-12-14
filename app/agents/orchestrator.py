from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator
import asyncio
import random
from datetime import datetime, timezone
from loguru import logger
from app.config import settings
from app.generators.text_generator import TextGenerator
from app.generators.image_generator import ImageGenerator
from app.automation.playwright_bot import PlaywrightTwitterBot
from app.storage import SessionLocal
from app.storage.models import Mention, Tweet, TweetStatus


class AgentState(TypedDict):
    mentions: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    content: List[Dict[str, Any]]
    errors: Annotated[List[str], operator.add]
    failed: bool  # Track if critical step failed


class TwitterAgentOrchestrator:
    def __init__(self):
        self.text_gen = TextGenerator()
        self.image_gen = ImageGenerator()
        self._bot: Optional[PlaywrightTwitterBot] = None
    
    async def run(self) -> Dict[str, Any]:
        logger.info("🤖 Starting agent workflow...")
        
        state: AgentState = {
            "mentions": [],
            "responses": [],
            "content": [],
            "errors": [],
            "failed": False
        }
        
        try:
            # Use single browser instance for entire workflow
            async with PlaywrightTwitterBot() as bot:
                self._bot = bot
                await bot.login()
                
                # Step 1: Fetch mentions
                state = await self._listen(state)
                
                # SHORT-CIRCUIT: Don't continue if listen failed
                if state["failed"]:
                    logger.warning("⚠️ Listen failed, skipping respond/execute")
                    return state
                
                # SHORT-CIRCUIT: No mentions to process
                if not state["mentions"]:
                    logger.info("No new mentions to process")
                    return state
                
                # Step 2: Generate responses
                state = await self._respond(state)
                
                # Step 3: Execute actions
                state = await self._execute(state)
            
            logger.success("✅ Workflow completed")
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            state["errors"].append(str(e))
            state["failed"] = True
        finally:
            self._bot = None
        
        return state
    
    async def _listen(self, state: AgentState) -> AgentState:
        logger.info("🎧 Fetching mentions...")
        
        try:
            if not self._bot:
                raise RuntimeError("Bot not initialized")
            
            raw_mentions = await self._bot.get_mentions(limit=10)
            
            # Filter out self-mentions and invalid mentions
            bot_username = settings.TWITTER_USERNAME.lower()
            
            with SessionLocal() as db:
                try:
                    new_mentions = []
                    for m in raw_mentions:
                        # CRITICAL: Skip empty tweet_id
                        if not m.get("tweet_id"):
                            logger.warning(f"Skipping mention with empty tweet_id: {m}")
                            continue
                        
                        # CRITICAL: Skip self-replies
                        if m.get("username", "").lower() == bot_username:
                            logger.debug(f"Skipping self-mention from @{m['username']}")
                            continue
                        
                        # CRITICAL: Skip empty content
                        if not m.get("text", "").strip():
                            logger.warning(f"Skipping mention with empty text: {m}")
                            continue
                        
                        # Check if already processed
                        exists = db.query(Mention).filter(
                            Mention.twitter_id == m["tweet_id"]
                        ).first()
                        
                        if exists:
                            logger.debug(f"Skipping already processed mention: {m['tweet_id']}")
                            continue
                        
                        # Save to DB
                        db_mention = Mention(
                            twitter_id=m["tweet_id"],
                            author_username=m["username"],
                            content=m["text"],
                            mentioned_at=datetime.now(timezone.utc),
                            processed=False
                        )
                        db.add(db_mention)
                        new_mentions.append(m)
                    
                    db.commit()
                    state["mentions"] = new_mentions
                    logger.success(f"Found {len(new_mentions)} new mentions (filtered from {len(raw_mentions)})")
                except Exception as db_err:
                    db.rollback()
                    logger.error(f"DB error in listen: {db_err}")
                    raise db_err

        except Exception as e:
            logger.error(f"Listen failed: {e}")
            state["errors"].append(f"Listen: {e}")
            state["failed"] = True
        
        return state
    
    async def _respond(self, state: AgentState) -> AgentState:
        logger.info("💬 Generating responses...")
        
        if not state["mentions"]:
            return state
        
        with SessionLocal() as db:
            for mention in state["mentions"]:
                try:
                    response_text = await self.text_gen.generate_reply(
                        original_tweet=mention["text"],
                        author=mention["username"]
                    )
                    
                    if not response_text or not response_text.strip():
                        logger.warning(f"Empty response generated for @{mention['username']}, skipping")
                        state["errors"].append(f"Empty response for @{mention['username']}")
                        continue
                    
                    # Atomic commit for draft creation
                    try:
                        db_tweet = Tweet(
                            content=response_text,
                            status=TweetStatus.DRAFT,
                            generation_prompt=f"Reply to @{mention['username']}: {mention['text'][:100]}"
                        )
                        db.add(db_tweet)
                        db.commit()
                        db.refresh(db_tweet)
                        
                        state["responses"].append({
                            "mention_url": mention["url"],
                            "response_text": response_text,
                            "username": mention["username"],
                            "db_tweet_id": db_tweet.id,
                            "mention_twitter_id": mention["tweet_id"]
                        })
                    except Exception as db_err:
                        db.rollback()
                        logger.error(f"Failed to save draft for @{mention['username']}: {db_err}")
                        raise db_err
                        
                except Exception as e:
                    logger.error(f"Failed to generate response for @{mention['username']}: {e}")
                    state["errors"].append(f"Response gen for @{mention['username']}: {e}")
        
        logger.success(f"Generated {len(state['responses'])} responses")
        return state
    
    async def _execute(self, state: AgentState) -> AgentState:
        logger.info("🚀 Executing actions...")
        
        if settings.REQUIRE_HUMAN_REVIEW:
            logger.info("Human review required - responses saved as drafts")
            return state
        
        if not state["responses"]:
            logger.info("No responses to execute")
            return state
        
        if not self._bot:
            state["errors"].append("Execute: Bot not initialized")
            return state
        
        with SessionLocal() as db:
            for response in state["responses"]:
                try:
                    result = await self._bot.post_tweet(
                        content=response["response_text"],
                        reply_to_url=response["mention_url"]
                    )
                    
                    # Update tweet status
                    db_tweet = db.query(Tweet).filter(
                        Tweet.id == response["db_tweet_id"]
                    ).first()
                    if db_tweet:
                        db_tweet.status = TweetStatus.POSTED
                        db_tweet.posted_at = datetime.now(timezone.utc)
                        db_tweet.twitter_id = result.get("twitter_id")
                    
                    # Mark mention as responded AND processed here
                    db_mention = db.query(Mention).filter(
                        Mention.twitter_id == response["mention_twitter_id"]
                    ).first()
                    if db_mention:
                        db_mention.responded = True
                        db_mention.processed = True
                    
                    db.commit()
                    logger.success(f"Replied to @{response['username']}")
                    
                    # Rate limit delay
                    await asyncio.sleep(random.uniform(
                        settings.MIN_ACTION_DELAY,
                        settings.MAX_ACTION_DELAY
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to reply to @{response['username']}: {e}")
                    state["errors"].append(f"Reply to @{response['username']}: {e}")
                    
                    # Mark tweet as failed
                    try:
                        db_tweet = db.query(Tweet).filter(
                            Tweet.id == response["db_tweet_id"]
                        ).first()
                        if db_tweet:
                            db_tweet.status = TweetStatus.FAILED
                        db.commit()
                    except Exception:
                        db.rollback()
        
        return state
    
    async def create_content(self, topic: str, with_image: bool = False) -> Dict[str, Any]:
        """Generate original content for posting"""
        logger.info(f"Creating content about: {topic}")
        
        tweet_text = await self.text_gen.generate_tweet(topic=topic)
        
        # Validate response
        if not tweet_text or not tweet_text.strip():
            raise ValueError("Generated empty tweet content")
        
        result = {"text": tweet_text, "media": [], "topic": topic}
        
        if with_image and settings.ENABLE_IMAGE_GENERATION:
            try:
                image_path = await self.image_gen.generate(prompt=topic)
                result["media"].append(image_path)
            except Exception as e:
                logger.warning(f"Image generation failed, posting without image: {e}")
        
        return result

    async def post_content(self, content: Dict[str, Any]) -> bool:
        """Post generated content to Twitter"""
        if settings.REQUIRE_HUMAN_REVIEW:
            # Save as draft instead
            with SessionLocal() as db:
                db_tweet = Tweet(
                    content=content["text"],
                    status=TweetStatus.DRAFT,
                    has_image=bool(content.get("media")),
                    media_urls=content.get("media", []),
                    generation_prompt=f"Topic: {content.get('topic', 'unknown')}"
                )
                db.add(db_tweet)
                db.commit()
            logger.info("Content saved as draft (human review required)")
            return False

        logger.info("🚀 Posting new content...")
        try:
            async with PlaywrightTwitterBot() as bot:
                await bot.login()
                result = await bot.post_tweet(
                    content=content["text"],
                    media_paths=content.get("media")
                )
            
            # Save to DB
            with SessionLocal() as db:
                db_tweet = Tweet(
                    content=content["text"],
                    status=TweetStatus.POSTED,
                    posted_at=datetime.now(timezone.utc),
                    has_image=bool(content.get("media")),
                    media_urls=content.get("media", []),
                    twitter_id=result.get("twitter_id"),
                    generation_prompt=f"Topic: {content.get('topic', 'unknown')}"
                )
                db.add(db_tweet)
                db.commit()

            logger.success("✅ Content posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post content: {e}")
            # Save as failed draft
            with SessionLocal() as db:
                db_tweet = Tweet(
                    content=content["text"],
                    status=TweetStatus.FAILED,
                    has_image=bool(content.get("media")),
                    media_urls=content.get("media", [])
                )
                db.add(db_tweet)
                db.commit()
            return False
