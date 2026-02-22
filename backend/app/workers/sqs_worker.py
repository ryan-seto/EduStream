"""
SQS worker for scheduled tweet publishing.

Run via: python -m app.workers.sqs_worker
Polls SQS for messages, checks scheduled_at, and publishes to Twitter.
"""
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the backend directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings
from app.services.sqs_service import sqs_service
from app.services.twitter_service import twitter_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sqs_worker")
settings = get_settings()

# Graceful shutdown flag
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down gracefully...", signum)
    _shutdown = True


async def _update_db(content_id: int, success: bool, tweet_id: str | None = None,
                     tweet_url: str | None = None, error: str | None = None):
    """Update content and schedule records in the database."""
    from app.database import async_session_maker
    from app.models.content import Content, ContentStatus, Schedule, ScheduleStatus
    from sqlalchemy import select

    async with async_session_maker() as session:
        # Update content status
        result = await session.execute(select(Content).where(Content.id == content_id))
        content = result.scalar_one_or_none()
        if content:
            content.status = ContentStatus.PUBLISHED if success else ContentStatus.FAILED

        # Update the most recent pending schedule for this content
        result = await session.execute(
            select(Schedule)
            .where(Schedule.content_id == content_id)
            .where(Schedule.status == ScheduleStatus.PENDING)
            .order_by(Schedule.created_at.desc())
            .limit(1)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            if success:
                schedule.status = ScheduleStatus.PUBLISHED
                schedule.published_at = datetime.utcnow()
                schedule.platform_post_id = tweet_id
            else:
                schedule.status = ScheduleStatus.FAILED
                schedule.error_message = error

        await session.commit()


async def process_message(message: dict) -> bool:
    """Process a single SQS message. Returns True if processed successfully."""
    body = message["body"]
    content_id = body["content_id"]
    platform = body["platform"]
    caption = body["caption"]
    image_path = body["image_path"]
    scheduled_at_str = body.get("scheduled_at")

    # Check if scheduled time is in the future
    if scheduled_at_str:
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
        now = datetime.utcnow()
        if scheduled_at > now:
            seconds_until = (scheduled_at - now).total_seconds()
            logger.info("Content %d scheduled for %s (%.0fs from now), skipping",
                        content_id, scheduled_at_str, seconds_until)
            return False  # Don't delete — will become visible again after timeout

    logger.info("Publishing content %d to %s...", content_id, platform)

    if platform != "twitter":
        logger.warning("Unsupported platform: %s", platform)
        await _update_db(content_id, success=False, error=f"Unsupported platform: {platform}")
        return True  # Delete from queue to prevent retries

    try:
        result = await twitter_service.post_image(
            image_path=image_path,
            caption=caption,
        )
        tweet_id = result["tweet_id"]
        tweet_url = result["url"]
        logger.info("Published! Tweet: %s", tweet_url)

        await _update_db(content_id, success=True, tweet_id=tweet_id, tweet_url=tweet_url)
        return True

    except Exception as e:
        logger.error("Failed to publish content %d: %s", content_id, e)
        await _update_db(content_id, success=False, error=str(e))
        return True  # Delete from queue to prevent infinite retries


async def poll_loop():
    """Main polling loop."""
    logger.info("Starting SQS poll loop...")
    logger.info("Queue URL: %s", settings.sqs_queue_url)

    while not _shutdown:
        try:
            messages = sqs_service.receive_messages(max_messages=1)

            if not messages:
                continue

            for msg in messages:
                logger.info("Received message: %s", msg["message_id"])
                processed = await process_message(msg)

                if processed:
                    sqs_service.delete_message(msg["receipt_handle"])
                    logger.info("Deleted message %s", msg["message_id"])

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Error in poll loop: %s", e)
            time.sleep(5)  # Brief pause before retrying

    logger.info("Stopped.")


def main():
    if not settings.use_sqs:
        logger.error("SQS is not configured. Set SQS_QUEUE_URL and AWS credentials in .env")
        sys.exit(1)

    if not twitter_service.is_configured():
        logger.warning("Twitter is not configured. Publishing will fail.")

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    asyncio.run(poll_loop())


if __name__ == "__main__":
    main()
