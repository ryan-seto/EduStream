"""
Publishing routes for social media platforms.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.content import Content, ContentStatus, Schedule, ScheduleStatus, Platform, AppSetting
from app.api.deps import get_current_active_user, get_optional_user
from app.services.twitter_service import twitter_service
from app.config import get_settings

settings = get_settings()

router = APIRouter()


async def _get_publish_interval(db: AsyncSession) -> int:
    """Get publish interval from DB, falling back to env var."""
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == "publish_interval_minutes")
    )
    setting = result.scalar_one_or_none()
    return int(setting.value) if setting else settings.sqs_publish_interval_minutes


def _build_caption(content: Content, custom_caption: str | None = None) -> str:
    """Build tweet caption from content script data."""
    if custom_caption:
        return custom_caption
    script_data = content.script_data or {}
    tweet_text = script_data.get("tweet_text", "")
    if tweet_text:
        return tweet_text
    hook = script_data.get("hook_text", "")
    cta = script_data.get("cta_text", "")
    return f"{hook}\n\n{cta}" if cta else (hook or "Check this out!")


# Schemas
class PublishRequest(BaseModel):
    content_id: int
    platform: str = "twitter"
    caption: str | None = None  # Custom caption, uses default if not provided
    hashtags: list[str] | None = None


class PublishResponse(BaseModel):
    success: bool
    platform: str
    post_url: str | None = None
    post_id: str | None = None
    message: str


class PlatformStatus(BaseModel):
    platform: str
    configured: bool
    name: str


class QueueRequest(BaseModel):
    content_id: int
    platform: str = "twitter"
    scheduled_at: str | None = None  # ISO format datetime


# Routes
@router.get("/platforms")
async def get_available_platforms(
    _user: User | None = Depends(get_optional_user),
) -> list[PlatformStatus]:
    """Get list of available publishing platforms and their configuration status."""
    return [
        PlatformStatus(
            platform="twitter",
            configured=twitter_service.is_configured(),
            name="Twitter/X",
        ),
        # Add more platforms here as they're implemented
        PlatformStatus(
            platform="youtube",
            configured=False,
            name="YouTube Shorts",
        ),
        PlatformStatus(
            platform="tiktok",
            configured=False,
            name="TikTok",
        ),
        PlatformStatus(
            platform="instagram",
            configured=False,
            name="Instagram Reels",
        ),
    ]


@router.post("/publish", response_model=PublishResponse)
async def publish_content(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Publish content to a social media platform."""

    # Get the content
    result = await db.execute(select(Content).where(Content.id == request.content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    if content.status not in [ContentStatus.READY, ContentStatus.PUBLISHED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content is not ready for publishing. Status: {content.status.value}",
        )

    if not content.diagram_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content has no image to publish",
        )

    caption = _build_caption(content, request.caption)
    hashtags = request.hashtags or None

    # Publish based on platform
    if request.platform == "twitter":
        if not twitter_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Twitter is not configured. Please add API credentials to .env",
            )

        try:
            result = await twitter_service.post_image(
                image_path=content.diagram_path,
                caption=caption,
                hashtags=hashtags,
            )

            # Create schedule record
            schedule = Schedule(
                content_id=content.id,
                platform=Platform.TWITTER,
                scheduled_at=datetime.utcnow(),
                published_at=datetime.utcnow(),
                status=ScheduleStatus.PUBLISHED,
                platform_post_id=result["tweet_id"],
            )
            db.add(schedule)

            # Update content status
            content.status = ContentStatus.PUBLISHED
            await db.commit()

            return PublishResponse(
                success=True,
                platform="twitter",
                post_url=result["url"],
                post_id=result["tweet_id"],
                message="Successfully published to Twitter!",
            )

        except Exception as e:
            # Log the error and create failed schedule record
            schedule = Schedule(
                content_id=content.id,
                platform=Platform.TWITTER,
                scheduled_at=datetime.utcnow(),
                status=ScheduleStatus.FAILED,
                error_message=str(e),
            )
            db.add(schedule)
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to publish to Twitter: {str(e)}",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{request.platform}' is not yet supported",
        )


@router.get("/history/{content_id}")
async def get_publish_history(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    """Get publishing history for a piece of content."""
    result = await db.execute(
        select(Schedule)
        .where(Schedule.content_id == content_id)
        .order_by(Schedule.created_at.desc())
    )
    schedules = result.scalars().all()

    return [
        {
            "id": s.id,
            "platform": s.platform.value,
            "status": s.status.value,
            "published_at": s.published_at.isoformat() if s.published_at else None,
            "post_id": s.platform_post_id,
            "error": s.error_message,
        }
        for s in schedules
    ]


# ── SQS Queue Endpoints ─────────────────────────────────────────────────


@router.post("/queue")
async def queue_content(
    request: QueueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Queue a single content item for scheduled publishing via SQS."""
    if not settings.use_sqs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQS is not configured. Set SQS_QUEUE_URL and AWS credentials in .env",
        )

    result = await db.execute(select(Content).where(Content.id == request.content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.status not in [ContentStatus.READY, ContentStatus.PUBLISHED]:
        raise HTTPException(
            status_code=400,
            detail=f"Content is not ready for queuing. Status: {content.status.value}",
        )

    if not content.diagram_path:
        raise HTTPException(status_code=400, detail="Content has no image to publish")

    # Determine scheduled time
    if request.scheduled_at:
        scheduled_at = datetime.fromisoformat(request.scheduled_at)
    else:
        # Schedule after the last pending item, or now + interval
        last_pending = await db.execute(
            select(func.max(Schedule.scheduled_at))
            .where(Schedule.status == ScheduleStatus.PENDING)
        )
        last_time = last_pending.scalar()
        interval_mins = await _get_publish_interval(db)
        if last_time:
            scheduled_at = last_time + timedelta(minutes=interval_mins)
        else:
            scheduled_at = datetime.utcnow() + timedelta(minutes=5)

    caption = _build_caption(content)

    # Send to SQS
    from app.services.sqs_service import sqs_service
    msg_id = sqs_service.enqueue_publish(
        content_id=content.id,
        platform=request.platform,
        caption=caption,
        image_path=content.diagram_path,
        scheduled_at=scheduled_at,
    )

    # Create schedule record
    schedule = Schedule(
        content_id=content.id,
        platform=Platform(request.platform),
        scheduled_at=scheduled_at,
        status=ScheduleStatus.PENDING,
    )
    db.add(schedule)

    # Update content status to QUEUED
    content.status = ContentStatus.QUEUED
    await db.commit()
    await db.refresh(schedule)

    return {
        "message": f"Queued for publishing at {scheduled_at.isoformat()}",
        "schedule_id": schedule.id,
        "scheduled_at": scheduled_at.isoformat(),
        "sqs_message_id": msg_id,
    }


@router.post("/queue-all")
async def queue_all_ready(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Queue all READY content with spread-out timing."""
    if not settings.use_sqs:
        raise HTTPException(
            status_code=400,
            detail="SQS is not configured.",
        )

    result = await db.execute(
        select(Content)
        .where(Content.status == ContentStatus.READY)
        .where(Content.diagram_path.isnot(None))
        .order_by(Content.created_at.asc())
    )
    ready_content = result.scalars().all()

    if not ready_content:
        return {"message": "No ready content to queue", "queued_count": 0}

    # Find last pending schedule time
    last_pending = await db.execute(
        select(func.max(Schedule.scheduled_at))
        .where(Schedule.status == ScheduleStatus.PENDING)
    )
    last_time = last_pending.scalar() or datetime.utcnow()
    interval_mins = await _get_publish_interval(db)
    interval = timedelta(minutes=interval_mins)

    from app.services.sqs_service import sqs_service
    queued_count = 0

    for content in ready_content:
        scheduled_at = last_time + interval * (queued_count + 1)

        caption = _build_caption(content)

        sqs_service.enqueue_publish(
            content_id=content.id,
            platform="twitter",
            caption=caption,
            image_path=content.diagram_path,
            scheduled_at=scheduled_at,
        )

        schedule = Schedule(
            content_id=content.id,
            platform=Platform.TWITTER,
            scheduled_at=scheduled_at,
            status=ScheduleStatus.PENDING,
        )
        db.add(schedule)
        content.status = ContentStatus.QUEUED
        queued_count += 1

    await db.commit()

    return {
        "message": f"Queued {queued_count} items for publishing",
        "queued_count": queued_count,
    }


@router.get("/queue-status")
async def get_queue_status(
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    """Get queue status: pending items and SQS stats."""
    result = await db.execute(
        select(Schedule)
        .where(Schedule.status == ScheduleStatus.PENDING)
        .order_by(Schedule.scheduled_at.asc())
    )
    pending = result.scalars().all()

    sqs_count = 0
    if settings.use_sqs:
        try:
            from app.services.sqs_service import sqs_service
            attrs = sqs_service.get_queue_attributes()
            sqs_count = int(attrs.get("ApproximateNumberOfMessages", 0))
        except Exception:
            pass

    return {
        "pending_items": [
            {
                "content_id": s.content_id,
                "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "status": s.status.value,
            }
            for s in pending
        ],
        "sqs_approximate_count": sqs_count,
    }
