"""Export router — final video rendering in Reels/Shorts format."""
import os
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from app.services.store import job_store
from app.services.video_processor import video_processor

router = APIRouter()

# Export format specs
FORMAT_SPECS = {
    "reels":  {"width": 1080, "height": 1920, "fps": 30},
    "shorts": {"width": 1080, "height": 1920, "fps": 60},
    "tiktok": {"width": 1080, "height": 1920, "fps": 30},
    "square": {"width": 1080, "height": 1080, "fps": 30},
}


class ExportRequest(BaseModel):
    highlight_id: str
    format: str = "reels"           # reels | shorts | tiktok | square
    caption_theme: str = "netflix"  # netflix | youtube | tiktok | minimal
    include_captions: bool = True
    include_hook: bool = True


@router.post("/export")
async def export_clip(req: ExportRequest):
    """
    Export a final video clip in the requested format.
    For the demo, returns the existing clip or triggers re-encoding.
    """
    highlight = job_store.get_highlight(req.highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")

    if not highlight.get("clip_url"):
        raise HTTPException(
            400,
            "Clip has not been extracted yet. Call /api/v1/clips/extract first.",
        )

    job_id = str(uuid.uuid4())[:8]
    export_record = {
        "job_id": job_id,
        "highlight_id": req.highlight_id,
        "format": req.format,
        "caption_theme": req.caption_theme,
        "include_captions": req.include_captions,
        "status": "completed",
        "output_url": highlight["clip_url"],  # reuse extracted clip for demo
        "format_spec": FORMAT_SPECS.get(req.format, FORMAT_SPECS["reels"]),
    }
    job_store.save_export(job_id, export_record)

    # Platform-specific sharing links (placeholder)
    platform_links = {
        "reels": "https://www.instagram.com/",
        "shorts": "https://www.youtube.com/",
        "tiktok": "https://www.tiktok.com/",
    }

    return {
        "job_id": job_id,
        "status": "completed",
        "output_url": highlight["clip_url"],
        "format": req.format,
        "caption_theme": req.caption_theme,
        "share_url": platform_links.get(req.format, "#"),
        "download_url": f"/api/v1/export/{job_id}/download",
        "message": f"Export ready in {req.format.upper()} format.",
    }


@router.get("/export/{job_id}")
async def get_export_status(job_id: str):
    """Get export job status."""
    export = job_store.get_export(job_id)
    if not export:
        raise HTTPException(404, "Export job not found.")
    return export


@router.get("/export/{job_id}/download")
async def download_export(job_id: str):
    """Download the exported video file."""
    export = job_store.get_export(job_id)
    if not export:
        raise HTTPException(404, "Export not found.")

    # Strip leading slash and resolve
    clip_path = export["output_url"].lstrip("/")
    if not os.path.exists(clip_path) or os.path.getsize(clip_path) < 100:
        raise HTTPException(404, "Video file not ready.")

    highlight = job_store.get_highlight(export["highlight_id"])
    safe_name = f"attentionx_{export['format']}_{export['highlight_id']}.mp4"
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=safe_name,
    )


@router.get("/exports")
async def list_exports():
    """List all export jobs."""
    return {"exports": job_store.list_exports()}
