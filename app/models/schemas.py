"""
Pydantic models for AttentionX AI
"""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class VideoStatus(str, Enum):
    uploaded = "uploaded"
    analyzing = "analyzing"
    analyzed = "analyzed"
    processing = "processing"
    ready = "ready"
    error = "error"


class CaptionTheme(str, Enum):
    netflix = "netflix"
    youtube = "youtube"
    tiktok = "tiktok"
    minimal = "minimal"


class ExportFormat(str, Enum):
    reels = "reels"          # 9:16, 1080x1920
    shorts = "shorts"        # 9:16, 1080x1920
    tiktok = "tiktok"        # 9:16, 1080x1920
    square = "square"        # 1:1, 1080x1080


class VideoMeta(BaseModel):
    video_id: str
    filename: str
    duration: float
    fps: float
    width: int
    height: int
    file_size_mb: float
    status: VideoStatus = VideoStatus.uploaded


class Highlight(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    duration: float
    virality_score: float          # 0–100
    energy_score: float            # audio energy
    sentiment_score: float         # positive sentiment
    topic: str
    description: str
    hook_title: str
    thumbnail_url: Optional[str] = None
    clip_url: Optional[str] = None


class Caption(BaseModel):
    start: float
    end: float
    text: str
    word_timings: Optional[List[dict]] = None


class ExportJob(BaseModel):
    job_id: str
    highlight_id: str
    format: ExportFormat
    caption_theme: CaptionTheme
    include_captions: bool = True
    include_music: bool = False
    status: str = "queued"
    output_url: Optional[str] = None


class AnalysisResult(BaseModel):
    video_id: str
    highlights: List[Highlight]
    total_clips: int
    processing_time_sec: float
    summary: str


class DashboardStats(BaseModel):
    total_videos: int
    total_clips: int
    avg_virality_score: float
    top_topics: List[str]
    clips_by_format: dict
