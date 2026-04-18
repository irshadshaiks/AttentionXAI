"""Dashboard router — analytics and stats."""
from fastapi import APIRouter
from app.services.store import job_store

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Return platform-wide analytics."""
    return job_store.get_stats()


@router.get("/dashboard/recent")
async def get_recent_clips(limit: int = 6):
    """Return most recent clips sorted by virality score."""
    highlights = job_store.list_highlights()
    highlights.sort(key=lambda h: h.get("virality_score", 0), reverse=True)
    return {"clips": highlights[:limit]}


@router.get("/dashboard/leaderboard")
async def get_leaderboard():
    """Top 10 clips by virality score."""
    highlights = job_store.list_highlights()
    highlights.sort(key=lambda h: h.get("virality_score", 0), reverse=True)
    return {"leaderboard": highlights[:10]}
