"""Captions router — Whisper transcription + SRT export."""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional

from app.services.store import job_store
from app.services.caption_generator import caption_generator
from app.services.ai_analyzer import ai_analyzer

router = APIRouter()


class CaptionRequest(BaseModel):
    highlight_id: str
    language: str = "en"


@router.post("/captions/generate")
async def generate_captions(req: CaptionRequest):
    """
    Generate word-by-word timed captions for a clip using Whisper.
    Also updates the AI analysis with actual transcript text.
    """
    highlight = job_store.get_highlight(req.highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")

    video = job_store.get_video(highlight["video_id"])
    if not video:
        raise HTTPException(404, "Source video not found.")

    # Use the original video as audio source (clip extraction optional)
    audio_path = video["stored_path"]

    captions = caption_generator.generate_captions(audio_path, language=req.language)

    # Filter captions to the highlight time window
    start = highlight["start_time"]
    end = highlight["end_time"]
    segment_captions = [
        {**c, "start": c["start"] - start, "end": c["end"] - start}
        for c in captions
        if c["start"] >= start and c["end"] <= end
    ]

    if not segment_captions:
        # Fallback: just take first N captions
        segment_captions = captions[: min(6, len(captions))]

    # Update highlight with transcript for better hooks
    full_text = " ".join(c["text"] for c in segment_captions)
    if full_text and not highlight.get("key_insight"):
        topic = highlight.get("topic", "Motivation")
        hook = ai_analyzer.generate_hook(topic, full_text)
        highlight["hook_title"] = hook
        highlight["key_insight"] = full_text[:200]

    highlight["captions"] = segment_captions
    job_store.save_highlight(req.highlight_id, highlight)

    # Save SRT file
    srt_dir = os.path.join("outputs", "captions")
    os.makedirs(srt_dir, exist_ok=True)
    srt_path = os.path.join(srt_dir, f"{req.highlight_id}.srt")
    caption_generator.save_srt(segment_captions, srt_path)

    return {
        "highlight_id": req.highlight_id,
        "captions": segment_captions,
        "total_segments": len(segment_captions),
        "full_text": full_text,
        "srt_url": f"/outputs/captions/{req.highlight_id}.srt",
        "language": req.language,
    }


@router.get("/captions/{highlight_id}")
async def get_captions(highlight_id: str):
    """Get generated captions for a clip."""
    highlight = job_store.get_highlight(highlight_id)
    if not highlight:
        raise HTTPException(404, "Highlight not found.")
    return {
        "highlight_id": highlight_id,
        "captions": highlight.get("captions", []),
    }


@router.get("/captions/{highlight_id}/srt", response_class=PlainTextResponse)
async def download_srt(highlight_id: str):
    """Download SRT subtitle file."""
    srt_path = os.path.join("outputs", "captions", f"{highlight_id}.srt")
    if not os.path.exists(srt_path):
        raise HTTPException(404, "SRT file not found. Generate captions first.")
    return open(srt_path, encoding="utf-8").read()
