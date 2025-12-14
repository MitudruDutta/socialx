import asyncio
from app.tasks.celery_app import celery_app
from loguru import logger

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(name="app.tasks.scheduled_tasks.check_mentions")
def check_mentions():
    logger.info("Running scheduled mention check...")
    from app.agents.orchestrator import TwitterAgentOrchestrator
    
    orchestrator = TwitterAgentOrchestrator()
    result = run_async(orchestrator.run())
    
    logger.info(f"Mention check complete: {len(result.get('mentions', []))} found")
    return result

@celery_app.task(name="app.tasks.scheduled_tasks.health_check")
def health_check():
    logger.info("Running scheduled health check...")
    from app.monitoring.health_checker import HealthChecker
    
    checker = HealthChecker()
    result = run_async(checker.run_all_checks())
    
    if result["overall_status"] != "healthy":
        logger.warning(f"System unhealthy: {result}")
    
    return result

@celery_app.task(name="app.tasks.scheduled_tasks.cleanup_media")
def cleanup_media():
    logger.info("Running media cleanup...")
    from app.generators.image_generator import ImageGenerator
    
    gen = ImageGenerator()
    gen.cleanup_old_images(days=7)
    
    return {"status": "cleaned"}

@celery_app.task(name="app.tasks.scheduled_tasks.generate_and_post_content")
def generate_and_post_content():
    logger.info("Running scheduled content generation...")
    from app.agents.orchestrator import TwitterAgentOrchestrator
    from app.config import settings
    import random
    
    topics = settings.content_topics_list
    if not topics:
        logger.warning("No topics configured, skipping generation.")
        return {"status": "skipped", "reason": "no_topics"}

    topic = random.choice(topics)
    orchestrator = TwitterAgentOrchestrator()
    
    # Generate
    content = run_async(orchestrator.create_content(
        topic=topic, 
        with_image=settings.ENABLE_IMAGE_GENERATION
    ))
    
    # Post
    posted = run_async(orchestrator.post_content(content))
    
    return {
        "status": "posted" if posted else "skipped_or_failed",
        "topic": topic,
        "content": content
    }
