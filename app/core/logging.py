import sys
from pathlib import Path
from loguru import logger
from app.config import settings

def setup_logging():
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    
    logger.add(sys.stderr, format=log_format, level="DEBUG" if settings.DEBUG else "INFO")
    logger.add("logs/app.log", rotation="10 MB", retention="7 days", format=log_format, level="INFO")
    logger.add("logs/error.log", rotation="10 MB", retention="30 days", format=log_format, level="ERROR")
    
    return logger
