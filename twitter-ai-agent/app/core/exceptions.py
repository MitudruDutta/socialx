class TwitterAutomationError(Exception):
    """Base exception for Twitter automation errors"""
    pass

class RateLimitError(TwitterAutomationError):
    """Raised when rate limit is hit"""
    pass

class LoginError(TwitterAutomationError):
    """Raised when login fails"""
    pass

class SelectorError(TwitterAutomationError):
    """Raised when DOM selector fails"""
    pass

class ContentGenerationError(Exception):
    """Raised when content generation fails"""
    pass
