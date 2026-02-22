from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ContentType(str, enum.Enum):
    PROBLEM = "problem"  # Quiz/problem with answer options
    CONCEPT = "concept"  # Educational explainer


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    QUEUED = "queued"
    PUBLISHED = "published"
    FAILED = "failed"


class ScheduleStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    contents: Mapped[list["Content"]] = relationship(back_populates="topic")


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))

    # Content type
    content_type: Mapped[ContentType] = mapped_column(
        SQLEnum(ContentType, values_callable=lambda x: [e.value for e in x]),
        default=ContentType.PROBLEM
    )

    # Generated content
    script_text: Mapped[str] = mapped_column(Text, nullable=True)  # Plain text for TTS
    script_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # Structured script JSON
    diagram_path: Mapped[str] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[str] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str] = mapped_column(String(500), nullable=True)

    # Metadata
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(ContentStatus, values_callable=lambda x: [e.value for e in x]),
        default=ContentStatus.DRAFT
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    topic: Mapped["Topic"] = relationship(back_populates="contents")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="content")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("contents.id"))
    platform: Mapped[Platform] = mapped_column(
        SQLEnum(Platform, values_callable=lambda x: [e.value for e in x])
    )

    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    status: Mapped[ScheduleStatus] = mapped_column(
        SQLEnum(ScheduleStatus, values_callable=lambda x: [e.value for e in x]),
        default=ScheduleStatus.PENDING
    )
    platform_post_id: Mapped[str] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    content: Mapped["Content"] = relationship(back_populates="schedules")
