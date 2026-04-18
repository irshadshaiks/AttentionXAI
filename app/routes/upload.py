"""Upload router — handles video file uploads."""
import os
import uuid
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.services.store import job_store
from app.services.video_processor import video_processor

router = APIRouter()

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 500))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")


def _ext(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a video file for processing."""
    if _ext(file.filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    video_id = str(uuid.uuid4())
    safe_name = f"{video_id}.{_ext(file.filename)}"
    dest = os.path.join(UPLOAD_DIR, safe_name)

    # Stream to disk
    total_bytes = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
                out.close()
                os.remove(dest)
                raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")
            out.write(chunk)

    # Extract metadata
    meta = video_processor.get_video_metadata(dest)

    video_record = {
        "video_id": video_id,
        "filename": file.filename,
        "stored_path": dest,
        "duration": meta["duration"],
        "fps": meta["fps"],
        "width": meta["width"],
        "height": meta["height"],
        "file_size_mb": meta["file_size_mb"],
        "status": "uploaded",
    }
    job_store.save_video(video_id, video_record)

    return {
        "video_id": video_id,
        "filename": file.filename,
        "duration": round(meta["duration"], 1),
        "file_size_mb": round(meta["file_size_mb"], 2),
        "width": meta["width"],
        "height": meta["height"],
        "fps": round(meta["fps"], 2),
        "status": "uploaded",
        "message": "Video uploaded successfully. Start analysis when ready.",
    }


@router.get("/videos")
async def list_videos():
    """List all uploaded videos."""
    return {"videos": job_store.list_videos()}


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    """Get video metadata by ID."""
    video = job_store.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    return video


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video and all associated data."""
    video = job_store.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    try:
        if os.path.exists(video["stored_path"]):
            os.remove(video["stored_path"])
    except Exception:
        pass
    return {"message": "Video deleted."}
