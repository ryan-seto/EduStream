from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.content import Topic, Content, ContentStatus
from app.api.deps import get_current_active_user, get_optional_user
from app.config import get_settings

settings = get_settings()

router = APIRouter()


# Schemas
class TopicCreate(BaseModel):
    name: str
    category: str
    description: str | None = None


class TopicResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    id: int
    topic_id: int
    content_type: str
    script_text: str | None
    script_data: dict | None
    diagram_path: str | None
    diagram_url: str | None = None
    audio_path: str | None
    video_path: str | None
    duration_seconds: int | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentWithTopicResponse(ContentResponse):
    topic: TopicResponse


# Topic Routes
@router.get("/topics", response_model=list[TopicResponse])
async def list_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Topic).order_by(Topic.created_at.desc()))
    return result.scalars().all()


@router.post("/topics", response_model=TopicResponse)
async def create_topic(
    topic_data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    topic = Topic(**topic_data.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found",
        )

    await db.delete(topic)
    await db.commit()
    return {"message": "Topic deleted"}


def _resolve_diagram_url(content: Content) -> str | None:
    """Resolve diagram_url from diagram_path based on storage backend."""
    if not content.diagram_path:
        return None
    path = content.diagram_path.replace("\\", "/")
    # S3 keys don't start with output/ or a drive letter
    if settings.use_s3 and not path.startswith(("output", "/", ".", "C:", "D:", "d:")):
        from app.services.s3_service import s3_service
        return s3_service.get_public_url(path)
    # Local file — strip to relative path and serve via /output mount
    # Handle absolute paths from older records
    output_marker = "output/"
    idx = path.find(output_marker)
    if idx != -1:
        relative = path[idx:]  # e.g. "output/diagrams/abc.png"
        return f"/{relative}"
    return f"/{path}"


def _content_to_response(content: Content) -> dict:
    """Convert a Content ORM object to a response dict with diagram_url."""
    data = ContentWithTopicResponse.model_validate(content).model_dump()
    data["diagram_url"] = _resolve_diagram_url(content)
    return data


# Content Routes
@router.get("/", response_model=list[ContentWithTopicResponse])
async def list_content(
    status_filter: ContentStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    query = select(Content).options(selectinload(Content.topic))

    if status_filter:
        query = query.where(Content.status == status_filter)

    query = query.order_by(Content.created_at.desc())
    result = await db.execute(query)
    contents = result.scalars().all()
    return [_content_to_response(c) for c in contents]


@router.get("/{content_id}", response_model=ContentWithTopicResponse)
async def get_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.topic))
        .where(Content.id == content_id)
    )
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    return _content_to_response(content)


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    await db.delete(content)
    await db.commit()
    return {"message": "Content deleted"}
