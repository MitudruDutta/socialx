from typing import Dict
from loguru import logger

class TwitterSelectors:
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
    
    async def get(self, element_name: str) -> str:
        return self._cache.get(element_name, self.DEFAULT_SELECTORS.get(element_name, ""))
    
    async def update_selector(self, element_name: str, new_selector: str):
        self._cache[element_name] = new_selector
        logger.info(f"Updated selector '{element_name}': {new_selector}")
    
    async def validate_selector(self, page, element_name: str) -> bool:
        try:
            selector = await self.get(element_name)
            element = await page.wait_for_selector(selector, timeout=5000)
            return element is not None
        except Exception:
            return False
