from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class TweetStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"

class ActionType(str, enum.Enum):
    POST = "post"
    REPLY = "reply"
    RETWEET = "retweet"
    LIKE = "like"

class Tweet(Base):
    __tablename__ = "tweets"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    twitter_id = Column(String(50), unique=True, nullable=True, index=True)
    status = Column(SQLEnum(TweetStatus), default=TweetStatus.DRAFT, index=True)
    has_image = Column(Boolean, default=False)
    media_urls = Column(JSON, default=lambda: [])
    hashtags = Column(JSON, default=lambda: [])
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    likes_count = Column(Integer, default=0)
    retweets_count = Column(Integer, default=0)
    generation_prompt = Column(Text, nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    parent_tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", index=True)
    goal = Column(String(500), nullable=False)
    topics = Column(JSON, default=lambda: [])
    posting_schedule = Column(JSON, default=lambda: {})
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Mention(Base):
    __tablename__ = "mentions"
    
    id = Column(Integer, primary_key=True, index=True)
    twitter_id = Column(String(50), unique=True, nullable=False, index=True)
    author_username = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    processed = Column(Boolean, default=False, index=True)
    responded = Column(Boolean, default=False)
    sentiment = Column(String(20), nullable=True)
    priority = Column(Integer, default=1)
    mentioned_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Action(Base):
    __tablename__ = "actions"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(SQLEnum(ActionType), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    target_url = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TwitterSelector(Base):
    __tablename__ = "twitter_selectors"
    
    id = Column(Integer, primary_key=True, index=True)
    element_name = Column(String(100), unique=True, nullable=False, index=True)
    selector = Column(String(500), nullable=False)
    selector_type = Column(String(20), default="css")
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_status = Column(String(20), default="unknown")
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
