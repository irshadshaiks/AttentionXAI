"""Analyze router — AI emotional peak detection + virality scoring."""
import os
import uuid
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.store import job_store
from app.services.video_processor import video_processor
from app.services.ai_analyzer import ai_analyzer

router = APIRouter()


class AnalyzeRequest(BaseModel):
    video_id: str
    min_clip_duration: float = 25.0
    max_clip_duration: float = 60.0
    max_clips: int = 8
    language: str = "en"


@router.post("/analyze")
async def analyze_video(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Trigger AI analysis of a video:
    1. Audio energy peak detection (Librosa)
    2. Per-segment AI analysis (Gemini)
    3. Virality score computation
    Returns list of timestamped highlights.
    """
    video = job_store.get_video(req.video_id)
    if not video:
        raise HTTPException(404, "Video not found.")

    job_store.update_video_status(req.video_id, "analyzing")
    start_time = time.time()

    # ── Step 1: Detect audio peaks ──────────────────────────────────────
    peaks = video_processor.detect_audio_peaks(
        video["stored_path"],
        min_duration=req.min_clip_duration,
        max_duration=req.max_clip_duration,
    )
    peaks = peaks[: req.max_clips]

    # ── Step 2: AI Analysis per segment ─────────────────────────────────
    highlights = []
    for peak in peaks:
        highlight_id = str(uuid.uuid4())[:8]
        
        # Fast extract of audio for Gemini
        audio_path = video_processor.extract_audio_clip(
            video["stored_path"],
            peak["start_time"],
            peak["end_time"],
            highlight_id
        )
        
        ai_result = ai_analyzer.analyze_segment(
            video_id=req.video_id,
            transcript_snippet="",
            energy_score=peak["energy_score"],
            start_time=peak["start_time"],
            end_time=peak["end_time"],
            audio_path=audio_path
        )

        duration = peak["end_time"] - peak["start_time"]
        sentiment = ai_result.get("sentiment_score", 75.0)
        topic = ai_result.get("topic", "Motivation")
        transcript = ai_result.get("transcript", "Captions not generated.")

        virality = ai_analyzer.predict_virality(
            energy_score=peak["energy_score"],
            sentiment_score=sentiment,
            topic=topic,
            duration=duration,
        )

        hook = ai_result.get("hook_title") or ai_analyzer.generate_hook(topic)

        # Generate thumbnail
        mid_time = peak["start_time"] + duration / 2
        try:
            thumb_path = video_processor.generate_thumbnail(
                video["stored_path"], mid_time, highlight_id
            )
            thumb_url = f"/outputs/thumbnails/{highlight_id}.jpg"
        except Exception:
            thumb_url = None

        highlight = {
            "id": highlight_id,
            "video_id": req.video_id,
            "start_time": peak["start_time"],
            "end_time": peak["end_time"],
            "duration": round(duration, 1),
            "energy_score": peak["energy_score"],
            "sentiment_score": sentiment,
            "virality_score": virality,
            "topic": topic,
            "description": ai_result.get("description", f"High-energy {topic} segment."),
            "hook_title": hook,
            "key_insight": ai_result.get("key_insight", ""),
            "thumbnail_url": thumb_url,
            "clip_url": None,
            "captions": [{"start": 0, "end": round(duration, 1), "text": transcript}] if transcript else None,
        }
        
        # Cleanup temp audio
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
                
        highlights.append(highlight)
        job_store.save_highlight(highlight_id, highlight)

    # Sort by virality (highest first)
    highlights.sort(key=lambda h: h["virality_score"], reverse=True)

    elapsed = round(time.time() - start_time, 2)
    job_store.update_video_status(req.video_id, "analyzed")

    return {
        "video_id": req.video_id,
        "highlights": highlights,
        "total_clips": len(highlights),
        "processing_time_sec": elapsed,
        "summary": (
            f"Found {len(highlights)} high-impact moments. "
            f"Top clip virality: {highlights[0]['virality_score'] if highlights else 0}%."
        ),
    }


@router.get("/analyze/{video_id}/status")
async def get_analysis_status(video_id: str):
    """Get current analysis status for a video."""
    video = job_store.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found.")
    highlights = job_store.get_highlights_for_video(video_id)
    return {
        "status": video.get("status", "unknown"),
        "highlight_count": len(highlights),
    }
