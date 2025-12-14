import asyncio
from app.tasks.celery_app import celery_app
from loguru import logger


def run_async(coro):
    """
    Run async coroutine in Celery sync context.
    
    Celery workers (prefork pool) are sync - they don't have a running event loop.
    We use asyncio.run() which creates a new loop, runs the coro, then closes it.
    
    This is safe for prefork workers. For gevent/eventlet, you'd need different handling.
    """
    # Celery prefork workers don't have a running loop
    # asyncio.run() is the cleanest approach
    return asyncio.run(coro)


def _handle_task_timeout(signum, frame):
    """Handle task timeout gracefully"""
    raise TimeoutError("Task exceeded time limit")


@celery_app.task(
    name="app.tasks.scheduled_tasks.check_mentions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=540,  # 9 minutes soft limit
    time_limit=600  # 10 minutes hard limit
)
def check_mentions(self):
    logger.info("Running scheduled mention check...")
    
    try:
        from app.agents.orchestrator import TwitterAgentOrchestrator
        
        orchestrator = TwitterAgentOrchestrator()
        result = run_async(orchestrator.run())
        
        mentions_count = len(result.get('mentions', []))
        errors_count = len(result.get('errors', []))
        
        logger.info(f"Mention check complete: {mentions_count} mentions, {errors_count} errors")
        
        # Alert on errors
        if errors_count > 0:
            _send_alert_sync(
                level="warning",
                title="Mention Check Errors",
                message=f"Found {errors_count} errors: {result['errors'][:3]}"
            )
        
        return {
            "status": "completed",
            "mentions": mentions_count,
            "errors": errors_count
        }
        
    except Exception as e:
        logger.error(f"Mention check failed: {e}")
        _send_alert_sync("error", "Mention Check Failed", str(e))
        raise self.retry(exc=e)


@celery_app.task(
    name="app.tasks.scheduled_tasks.health_check",
    bind=True,
    soft_time_limit=60,
    time_limit=90
)
def health_check(self):
    logger.info("Running scheduled health check...")
    
    try:
        from app.monitoring.health_checker import HealthChecker
        
        async def run_check():
            checker = HealthChecker()
            try:
                return await checker.run_all_checks()
            finally:
                await checker.close()
        
        result = run_async(run_check())
        
        if result["overall_status"] != "healthy":
            logger.warning(f"System unhealthy: {result}")
            
            unhealthy = [k for k, v in result["checks"].items() if not v.get("healthy")]
            _send_alert_sync(
                level="error",
                title="System Health Alert",
                message=f"Unhealthy: {', '.join(unhealthy)}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.scheduled_tasks.cleanup_media")
def cleanup_media():
    logger.info("Running media cleanup...")
    
    try:
        from app.generators.image_generator import ImageGenerator
        
        gen = ImageGenerator()
        gen.cleanup_old_images(days=7)
        gen.unload_model()
        
        return {"status": "cleaned"}
        
    except Exception as e:
        logger.error(f"Media cleanup failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(
    name="app.tasks.scheduled_tasks.generate_and_post_content",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=540,
    time_limit=600
)
def generate_and_post_content(self):
    logger.info("Running scheduled content generation...")
    
    try:
        from app.agents.orchestrator import TwitterAgentOrchestrator
        from app.config import settings
        import random
        
        topics = settings.content_topics_list
        if not topics:
            logger.warning("No topics configured, skipping generation.")
            return {"status": "skipped", "reason": "no_topics"}

        topic = random.choice(topics)
        orchestrator = TwitterAgentOrchestrator()
        
        # Generate content
        content = run_async(orchestrator.create_content(
            topic=topic, 
            with_image=settings.ENABLE_IMAGE_GENERATION
        ))
        
        # Post content
        posted = run_async(orchestrator.post_content(content))
        
        status = "posted" if posted else "draft_saved"
        logger.info(f"Content generation complete: {status}")
        
        return {
            "status": status,
            "topic": topic,
            "text": content.get("text", "")[:100]
        }
        
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        _send_alert_sync("error", "Content Generation Failed", str(e))
        raise self.retry(exc=e)


def _send_alert_sync(level: str, title: str, message: str):
    """Send alert synchronously (for use in Celery tasks)"""
    try:
        from app.monitoring.alert_manager import AlertManager
        alert = AlertManager()
        run_async(alert.send_alert(level=level, title=title, message=message))
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
