from typing import List, Dict, Any
from loguru import logger
from app.automation.playwright_bot import PlaywrightTwitterBot

class MentionScraper:
    async def get_recent_mentions(self, limit: int = 20) -> List[Dict[str, Any]]:
        logger.info(f"Scraping {limit} recent mentions...")
        
        async with PlaywrightTwitterBot() as bot:
            await bot.login()
            mentions = await bot.get_mentions(limit=limit)
        
        return mentions
    
    async def get_hashtag_tweets(self, hashtag: str, limit: int = 20) -> List[Dict[str, Any]]:
        logger.info(f"Scraping #{hashtag}...")
        
        async with PlaywrightTwitterBot() as bot:
            await bot.initialize()
            await bot.login()
            
            await bot.page.goto(f"https://x.com/search?q=%23{hashtag}&src=typed_query&f=live")
            await bot._delay(3, 5)
            
            tweets = []
            elements = await bot.page.query_selector_all('article[data-testid="tweet"]')
            
            for el in elements[:limit]:
                try:
                    tweets.append(await bot._extract_tweet(el))
                except:
                    continue
            
            return tweets
