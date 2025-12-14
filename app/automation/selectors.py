from typing import Dict
from loguru import logger
import asyncio


class TwitterSelectors:
    """
    Manages Twitter DOM selectors with DB persistence support.
    Falls back to hardcoded defaults if DB unavailable.
    """
    
    DEFAULT_SELECTORS = {
        "login_username_input": 'input[autocomplete="username"]',
        "login_next_button": '[role="button"]:has-text("Next")',
        "login_password_input": 'input[autocomplete="current-password"]',
        "login_button": '[data-testid="LoginForm_Login_Button"]',
        "tweet_compose_box": '[data-testid="tweetTextarea_0"]',
        "tweet_post_button": '[data-testid="tweetButtonInline"]',
        "media_upload_input": 'input[data-testid="fileInput"]',
        "reply_button": '[data-testid="reply"]',
        "reply_send_button": '[data-testid="tweetButton"]',
        "tweet_article": 'article[data-testid="tweet"]',
        "tweet_text": '[data-testid="tweetText"]',
        "tweet_user": '[data-testid="User-Name"]',
    }
    
    def __init__(self):
        self._cache: Dict[str, str] = self.DEFAULT_SELECTORS.copy()
        self._db_loaded = False
    
    def load_from_db(self) -> bool:
        """Load selectors from database (sync, call once at startup)"""
        if self._db_loaded:
            return True
        
        try:
            from app.storage import SessionLocal
            from app.storage.models import TwitterSelector
            
            with SessionLocal() as db:
                db_selectors = db.query(TwitterSelector).filter(
                    TwitterSelector.validation_status != "invalid"
                ).all()
                
                for sel in db_selectors:
                    self._cache[sel.element_name] = sel.selector
                
                if db_selectors:
                    logger.info(f"Loaded {len(db_selectors)} selectors from DB")
                
                self._db_loaded = True
                return True
                
        except Exception as e:
            logger.warning(f"Could not load selectors from DB, using defaults: {e}")
            return False
    
    async def get(self, element_name: str) -> str:
        """Get selector by name, tries DB first then defaults"""
        if not self._db_loaded:
            await asyncio.to_thread(self.load_from_db)
        
        selector = self._cache.get(element_name)
        if selector:
            return selector
        
        # Fallback to default
        default = self.DEFAULT_SELECTORS.get(element_name, "")
        if not default:
            logger.warning(f"Unknown selector requested: {element_name}")
        return default
    
    async def update_selector(self, element_name: str, new_selector: str, persist: bool = True):
        """Update selector in memory and optionally persist to DB"""
        old_selector = self._cache.get(element_name)
        
        if persist:
            try:
                from app.storage import SessionLocal
                from app.storage.models import TwitterSelector
                from datetime import datetime, timezone
                
                # Perform DB update synchronously in thread to avoid blocking
                def _persist_update():
                    with SessionLocal() as db:
                        existing = db.query(TwitterSelector).filter(
                            TwitterSelector.element_name == element_name
                        ).first()
                        
                        if existing:
                            existing.selector = new_selector
                            existing.last_validated = datetime.now(timezone.utc)
                            existing.validation_status = "valid"
                            existing.failure_count = 0
                        else:
                            db.add(TwitterSelector(
                                element_name=element_name,
                                selector=new_selector,
                                last_validated=datetime.now(timezone.utc),
                                validation_status="valid"
                            ))
                        db.commit()
                
                await asyncio.to_thread(_persist_update)
                logger.info(f"Persisted selector '{element_name}': {new_selector}")
                
                # Update cache only after successful persistence
                self._cache[element_name] = new_selector
                
            except Exception as e:
                logger.error(f"Failed to persist selector to DB: {e}")
                # Do NOT update cache if persistence failed
                return
        else:
            self._cache[element_name] = new_selector
        
        logger.info(f"Updated selector '{element_name}': {old_selector} -> {new_selector}")
    
    async def mark_failed(self, element_name: str):
        """Mark a selector as failed (for tracking breakages)"""
        try:
            from app.storage import SessionLocal
            from app.storage.models import TwitterSelector
            
            def _mark_db():
                with SessionLocal() as db:
                    existing = db.query(TwitterSelector).filter(
                        TwitterSelector.element_name == element_name
                    ).first()
                    
                    if existing:
                        existing.failure_count += 1
                        if existing.failure_count >= 3:
                            existing.validation_status = "invalid"
                        db.commit()
            
            await asyncio.to_thread(_mark_db)
                    
        except Exception as e:
            logger.debug(f"Could not mark selector as failed: {e}")
    
    async def validate_selector(self, page, element_name: str) -> bool:
        """Validate if a selector still works on the page"""
        try:
            selector = await self.get(element_name)
            element = await page.wait_for_selector(selector, timeout=5000)
            return element is not None
        except Exception:
            await self.mark_failed(element_name)
            return False
