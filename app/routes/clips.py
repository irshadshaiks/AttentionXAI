"""Clips router — handles clip extraction and preview."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.services.store import job_store
from app.services.video_processor import video_processor

router = APIRouter()


class ClipRequest(BaseModel):
    highlight_id: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    vertical: bool = True


@router.post("/clips/extract")
async def extract_clip(req: ClipRequest, background_tasks: BackgroundTasks):
    """
    Extract a clip for a highlight. Optionally override start/end times.
    Converts to 9:16 vertical format with face tracking.
    """
    highlight = job_store.get_highlight(req.highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")

    video = job_store.get_video(highlight["video_id"])
    if not video:
        raise HTTPException(404, "Source video not found.")

    start = req.start_time if req.start_time is not None else highlight["start_time"]
    end = req.end_time if req.end_time is not None else highlight["end_time"]

    # Cap end to video duration
    end = min(end, video.get("duration", end))

    clip_path = video_processor.extract_clip(
        video["stored_path"],
        start_time=start,
        end_time=end,
        clip_id=req.highlight_id,
        vertical=req.vertical,
    )

    clip_url = f"/outputs/clips/{req.highlight_id}.mp4"

    # Update highlight record
    highlight["clip_url"] = clip_url
    highlight["start_time"] = start
    highlight["end_time"] = end
    highlight["duration"] = round(end - start, 1)
    job_store.save_highlight(req.highlight_id, highlight)

    return {
        "highlight_id": req.highlight_id,
        "clip_url": clip_url,
        "start_time": start,
        "end_time": end,
        "duration": round(end - start, 1),
        "vertical": req.vertical,
        "status": "ready",
    }


@router.get("/clips/{highlight_id}")
async def get_clip(highlight_id: str):
    """Get clip details for a highlight."""
    highlight = job_store.get_highlight(highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")
    return highlight


@router.get("/clips")
async def list_clips(video_id: Optional[str] = None):
    """List all clips, optionally filtered by video_id."""
    if video_id:
        clips = job_store.get_highlights_for_video(video_id)
    else:
        clips = job_store.list_highlights()
    return {"clips": clips, "total": len(clips)}


@router.put("/clips/{highlight_id}/trim")
async def trim_clip(highlight_id: str, start_time: float, end_time: float):
    """Update start/end time for a clip (re-extraction required)."""
    highlight = job_store.get_highlight(highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")
    highlight["start_time"] = start_time
    highlight["end_time"] = end_time
    highlight["duration"] = round(end_time - start_time, 1)
    highlight["clip_url"] = None  # invalidate
    job_store.save_highlight(highlight_id, highlight)
    return {"message": "Trim times updated. Re-extract clip to apply.", "highlight": highlight}
