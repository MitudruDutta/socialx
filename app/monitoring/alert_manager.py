from loguru import logger
from app.config import settings
import httpx

class AlertManager:
    async def send_alert(self, level: str, title: str, message: str):
        logger.log(level.upper(), f"{title}: {message}")
        
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            await self._send_telegram(level, title, message)
    
    async def _send_telegram(self, level: str, title: str, message: str):
        try:
            emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(level, "📢")
            text = f"{emoji} *{title}*\n\n{message}"
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": settings.TELEGRAM_CHAT_ID,
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
