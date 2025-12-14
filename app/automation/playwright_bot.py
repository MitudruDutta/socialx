from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from typing import Optional, Dict, List, Any
import asyncio
import json
import random
import os
import time
from pathlib import Path
from loguru import logger
from app.config import settings
from app.automation.stealth import apply_stealth_config
from app.automation.selectors import TwitterSelectors
from app.core.exceptions import TwitterAutomationError, RateLimitError

class PlaywrightTwitterBot:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_logged_in = False
        self.session_file = Path("data/twitter_session.json")
        self.selectors = TwitterSelectors()
        self.rate_limited = False
        self.rate_limit_until: float = 0
        
    async def initialize(self, headless: bool = True):
        logger.info("Initializing browser...")
        try:
            self.playwright = await async_playwright().start()
            
            # Start with secure defaults
            args = ['--disable-blink-features=AutomationControlled']
            
            # Only use --no-sandbox if explicitly requested (e.g. in Docker)
            if os.environ.get("DISABLE_SANDBOX", "false").lower() == "true":
                args.append('--no-sandbox')
                logger.warning("Running with --no-sandbox (insecure)")
            
            launch_options = {
                "headless": headless,
                "args": args,
            }
            
            if settings.PROXY_HOST and settings.PROXY_PORT:
                proxy_config = {
                    "server": f"http://{settings.PROXY_HOST}:{settings.PROXY_PORT}"
                }
                if settings.PROXY_USERNAME and settings.PROXY_PASSWORD:
                    proxy_config["username"] = settings.PROXY_USERNAME
                    proxy_config["password"] = settings.PROXY_PASSWORD
                launch_options["proxy"] = proxy_config
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": self._get_user_agent(),
                "locale": "en-US",
            }
            
            if self.session_file.exists():
                try:
                    context_options["storage_state"] = json.loads(self.session_file.read_text())
                except Exception as e:
                    logger.warning(f"Failed to load session file: {e}")
            
            self.context = await self.browser.new_context(**context_options)
            await apply_stealth_config(self.context)
            self.page = await self.context.new_page()
            self.page.on("response", self._on_response)
            logger.success("Browser initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            await self.close()
            raise TwitterAutomationError(f"Initialization failed: {e}") from e
        
    async def login(self, force: bool = False) -> bool:
        if self.is_logged_in and not force:
            return True
        
        try:
            logger.info("Logging in to Twitter...")
            await self.page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
            await self._delay(2, 4)
            
            # Username
            username_input = await self.page.wait_for_selector(
                await self.selectors.get("login_username_input"), timeout=15000
            )
            await self._human_type(username_input, settings.TWITTER_USERNAME)
            await self._delay(1, 2)
            
            await self.page.click('[role="button"]:has-text("Next")')
            await self._delay(2, 3)
            
            # Check for verification
            try:
                verify_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', timeout=3000
                )
                await self._human_type(verify_input, settings.TWITTER_EMAIL)
                await self.page.click('[data-testid="ocfEnterTextNextButton"]')
                await self._delay(2, 3)
            except PlaywrightTimeoutError:
                pass
            
            # Password
            password_input = await self.page.wait_for_selector(
                await self.selectors.get("login_password_input"), timeout=15000
            )
            await self._human_type(password_input, settings.TWITTER_PASSWORD)
            await self._delay(1, 2)
            
            await self.page.click('[data-testid="LoginForm_Login_Button"]')
            await self.page.wait_for_url("**/home", timeout=30000)
            await self._delay(3, 5)
            
            # Save session
            storage_state = await self.context.storage_state()
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            self.session_file.write_text(json.dumps(storage_state, indent=2))
            
            self.is_logged_in = True
            logger.success("Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self._screenshot("login_error")
            raise TwitterAutomationError(f"Login failed: {e}")
    
    def _check_rate_limit(self):
        if self.rate_limited:
            if time.time() < self.rate_limit_until:
                raise RateLimitError("Rate limit active")
            else:
                self.rate_limited = False
                self.rate_limit_until = 0
                logger.info("Rate limit cooldown expired. Resuming operations.")

    async def post_tweet(self, content: str, media_paths: Optional[List[str]] = None, reply_to_url: Optional[str] = None) -> Dict[str, Any]:
        self._check_rate_limit()

        try:
            logger.info(f"Posting: {content[:50]}...")
            
            if reply_to_url:
                await self.page.goto(reply_to_url, wait_until="domcontentloaded")
                await self._delay(2, 3)
                await self.page.click(await self.selectors.get("reply_button"))
            else:
                await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
                await self._delay(2, 3)
            
            tweet_box = await self.page.wait_for_selector(
                await self.selectors.get("tweet_compose_box"), timeout=10000
            )
            await self._human_type(tweet_box, content)
            await self._delay(1, 2)
            
            if media_paths:
                for path in media_paths:
                    if not Path(path).exists():
                        raise TwitterAutomationError(f"Media file not found: {path}")
                    try:
                        await self.page.set_input_files(
                            await self.selectors.get("media_upload_input"), path
                        )
                        await self._delay(2, 3)
                    except Exception as e:
                        logger.error(f"Failed to upload media {path}: {e}")
                        raise TwitterAutomationError(f"Media upload failed: {e}")
            
            button_selector = await self.selectors.get("reply_send_button" if reply_to_url else "tweet_post_button")
            await self.page.click(button_selector)
            await self._delay(3, 5)
            
            logger.success("Tweet posted!")
            return {"success": True, "content": content}
            
        except (PlaywrightError, PlaywrightTimeoutError, asyncio.TimeoutError) as e:
            logger.error(f"Post failed: {e}")
            await self._screenshot("post_error")
            raise TwitterAutomationError(f"Post failed: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during post: {e}")
            await self._screenshot("post_fatal_error")
            raise TwitterAutomationError(f"Unexpected post error: {e}")
    
    async def get_mentions(self, limit: int = 20) -> List[Dict[str, Any]]:
        self._check_rate_limit()

        try:
            logger.info("Fetching mentions...")
            await self.page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded")
            await self._delay(3, 5)
            
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, 1000)")
                await self._delay(1, 2)
            
            mentions = []
            tweets = await self.page.query_selector_all(await self.selectors.get("tweet_article"))
            
            for tweet in tweets[:limit]:
                try:
                    mentions.append(await self._extract_tweet(tweet))
                except Exception:
                    continue
            
            logger.success(f"Found {len(mentions)} mentions")
            return mentions
        except Exception as e:
            logger.exception(f"Failed to fetch mentions: {e}")
            raise TwitterAutomationError(f"Failed to fetch mentions: {e}") from e
    
    async def _extract_tweet(self, element) -> Dict[str, Any]:
        user_el = await element.query_selector('[data-testid="User-Name"]')
        username = (await user_el.inner_text()).split('\n')[0].replace('@', '') if user_el else ""
        
        text_el = await element.query_selector('[data-testid="tweetText"]')
        text = await text_el.inner_text() if text_el else ""
        
        link_el = await element.query_selector('a[href*="/status/"]')
        href = await link_el.get_attribute('href') if link_el else ""
        
        return {
            "tweet_id": href.split('/')[-1] if href else "",
            "username": username,
            "text": text,
            "url": f"https://x.com{href}" if href else "",
        }
    
    async def _human_type(self, element, text: str):
        for char in text:
            await element.type(char, delay=random.randint(50, 150))
            if random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def _delay(self, min_s: float, max_s: float):
        await asyncio.sleep(random.uniform(min_s, max_s))
    
    def _get_user_agent(self) -> str:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    async def _screenshot(self, name: str):
        try:
            timestamp = int(time.time())
            path = Path(f"data/screenshots/{name}_{timestamp}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(path))
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")
    
    async def _on_response(self, response):
        if response.status == 429:
            self.rate_limited = True
            self.rate_limit_until = time.time() + 900  # 15 minutes
            logger.warning("Rate limit detected (429). Operations paused for 15 minutes.")
    
    async def close(self):
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
