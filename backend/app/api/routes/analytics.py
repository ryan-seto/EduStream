from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.content import Content, ContentStatus, Topic, Schedule, ScheduleStatus
from app.api.deps import get_optional_user

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Total counts by status
    status_query = select(
        Content.status, func.count(Content.id)
    ).group_by(Content.status)
    status_result = await db.execute(status_query)
    by_status = {row[0].value: row[1] for row in status_result.all()}

    total = sum(by_status.values())
    published = by_status.get("published", 0)

    # Counts by content type
    type_query = select(
        Content.content_type, func.count(Content.id)
    ).group_by(Content.content_type)
    type_result = await db.execute(type_query)
    by_type = {row[0].value: row[1] for row in type_result.all()}

    # This week count
    week_query = select(func.count(Content.id)).where(
        Content.created_at >= week_ago
    )
    this_week = (await db.execute(week_query)).scalar() or 0

    # This month count
    month_query = select(func.count(Content.id)).where(
        Content.created_at >= month_ago
    )
    this_month = (await db.execute(month_query)).scalar() or 0

    # Daily counts (last 30 days)
    daily_query = select(
        func.date(Content.created_at).label("date"),
        func.count(Content.id).label("count"),
    ).where(
        Content.created_at >= month_ago
    ).group_by(
        func.date(Content.created_at)
    ).order_by("date")
    daily_result = await db.execute(daily_query)
    daily_counts = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result.all()
    ]

    # Category counts (via topic join)
    cat_query = select(
        Topic.category, func.count(Content.id)
    ).join(
        Content, Content.topic_id == Topic.id
    ).group_by(Topic.category)
    cat_result = await db.execute(cat_query)
    category_counts = [
        {"category": row[0], "count": row[1]}
        for row in cat_result.all()
    ]

    # Recent publications (from Schedule)
    pub_query = select(
        Schedule.content_id,
        Schedule.platform,
        Schedule.published_at,
        Schedule.platform_post_id,
        Schedule.status,
        Content.script_data,
        Topic.name.label("topic_name"),
    ).join(
        Content, Content.id == Schedule.content_id
    ).join(
        Topic, Topic.id == Content.topic_id
    ).order_by(
        Schedule.created_at.desc()
    ).limit(10)
    pub_result = await db.execute(pub_query)
    recent_publications = []
    for row in pub_result.all():
        script = row.script_data or {}
        title = script.get("hook_text", row.topic_name) if isinstance(script, dict) else row.topic_name
        recent_publications.append({
            "content_id": row.content_id,
            "title": title,
            "platform": row.platform.value if hasattr(row.platform, 'value') else str(row.platform),
            "published_at": str(row.published_at) if row.published_at else None,
            "post_url": None,
            "status": row.status.value if hasattr(row.status, 'value') else str(row.status),
        })

    # Weekly published vs failed (last 8 weeks)
    eight_weeks_ago = now - timedelta(weeks=8)
    weekly_query = select(
        func.date(Schedule.created_at).label("date"),
        Schedule.status,
        func.count(Schedule.id).label("count"),
    ).where(
        Schedule.created_at >= eight_weeks_ago
    ).group_by(
        func.date(Schedule.created_at),
        Schedule.status,
    ).order_by("date")
    weekly_result = await db.execute(weekly_query)
    weekly_data = [
        {"date": str(row.date), "status": row.status.value if hasattr(row.status, 'value') else str(row.status), "count": row.count}
        for row in weekly_result.all()
    ]

    publish_rate = round((published / total * 100), 1) if total > 0 else 0

    return {
        "total_content": total,
        "by_status": by_status,
        "by_type": by_type,
        "this_week": this_week,
        "this_month": this_month,
        "daily_counts": daily_counts,
        "category_counts": category_counts,
        "recent_publications": recent_publications,
        "publish_rate": publish_rate,
        "weekly_publish_data": weekly_data,
    }
