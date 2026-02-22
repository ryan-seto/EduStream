import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, async_session_maker
from app.models.user import User
from app.models.content import Topic, Content, ContentStatus, ContentType
from app.api.deps import get_current_active_user
from app.services.ai_generator import ai_generator
from app.services.diagram_gen import diagram_generator

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class GenerateRequest(BaseModel):
    topic_name: str
    category: str = "engineering"
    description: str | None = None
    content_type: str = "problem"


class BatchGenerateRequest(BaseModel):
    topics: list[GenerateRequest]


class GenerateResponse(BaseModel):
    content_id: int
    status: str
    message: str


async def _get_or_create_topic(
    db: AsyncSession, name: str, category: str, description: str | None
) -> Topic:
    """Find an existing topic or create a new one."""
    result = await db.execute(
        select(Topic).where(Topic.name == name, Topic.category == category)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        topic = Topic(name=name, category=category, description=description)
        db.add(topic)
        await db.commit()
        await db.refresh(topic)
    return topic


async def _create_content(db: AsyncSession, topic_id: int, content_type_str: str) -> Content:
    """Create a new content record in GENERATING state."""
    content_type = ContentType.CONCEPT if content_type_str == "concept" else ContentType.PROBLEM
    content = Content(
        topic_id=topic_id,
        content_type=content_type,
        status=ContentStatus.GENERATING,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


# Background task for full pipeline
async def run_generation_pipeline(
    content_id: int,
    topic_name: str,
    category: str,
    description: str | None
):
    """
    Full generation pipeline:
    1. Generate script with AI
    2. Generate diagram
    """
    async with async_session_maker() as db:
        try:
            result = await db.execute(select(Content).where(Content.id == content_id))
            content = result.scalar_one_or_none()
            if not content:
                return

            # Step 1: Generate script with AI
            script_data = await ai_generator.generate_problem_script(
                topic=topic_name,
                category=category,
                description=description,
            )

            content.script_data = script_data
            content.script_text = script_data.get("hook_text", "") + " " + " ".join(
                step.get("text", "") for step in script_data.get("content_steps", [])
            )

            # Step 2: Generate diagram
            diagram_path = await diagram_generator.generate_from_description(
                title=script_data.get("hook_text", topic_name),
                description=script_data.get("diagram_description", ""),
                answer_options=script_data.get("answer_options", []),
                correct_answer=script_data.get("correct_answer"),
            )
            logger.info("Diagram saved to: %s", diagram_path)
            content.diagram_path = diagram_path

            content.status = ContentStatus.READY
            await db.commit()

        except Exception as e:
            logger.error("Generation failed for content %d: %s", content_id, e)
            result = await db.execute(select(Content).where(Content.id == content_id))
            content = result.scalar_one_or_none()
            if content:
                content.status = ContentStatus.FAILED
                content.error_message = str(e)
                await db.commit()


# Routes
@router.post("/single", response_model=GenerateResponse)
async def generate_single(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    topic = await _get_or_create_topic(db, request.topic_name, request.category, request.description)
    content = await _create_content(db, topic.id, request.content_type)

    background_tasks.add_task(
        run_generation_pipeline,
        content.id,
        request.topic_name,
        request.category,
        request.description,
    )

    return GenerateResponse(
        content_id=content.id,
        status="generating",
        message=f"Started generation for: {request.topic_name}",
    )


@router.post("/batch", response_model=list[GenerateResponse])
async def generate_batch(
    request: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if len(request.topics) > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 30 topics per batch",
        )

    responses = []
    for topic_request in request.topics:
        topic = await _get_or_create_topic(
            db, topic_request.topic_name, topic_request.category, topic_request.description
        )
        content = await _create_content(db, topic.id, topic_request.content_type)

        background_tasks.add_task(
            run_generation_pipeline,
            content.id,
            topic_request.topic_name,
            topic_request.category,
            topic_request.description,
        )

        responses.append(
            GenerateResponse(
                content_id=content.id,
                status="generating",
                message=f"Started generation for: {topic_request.topic_name}",
            )
        )

    return responses


@router.get("/status/{content_id}")
async def get_generation_status(
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

    return {
        "content_id": content.id,
        "status": content.status.value,
        "has_script": content.script_text is not None,
        "has_diagram": content.diagram_path is not None,
        "has_audio": content.audio_path is not None,
        "has_video": content.video_path is not None,
        "error_message": content.error_message,
        "script_data": content.script_data,
    }
