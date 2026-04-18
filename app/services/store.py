"""
In-memory store for jobs and video metadata.
In production, replace with a real database (PostgreSQL / Redis).
"""
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

_STORE_FILE = "outputs/store.json"


class JobStore:
    """Simple JSON-backed in-memory store."""

    def __init__(self):
        self._data: Dict[str, Any] = {
            "videos": {},
            "highlights": {},
            "exports": {},
        }
        self._load()

    def _load(self):
        if os.path.exists(_STORE_FILE):
            try:
                with open(_STORE_FILE, "r") as f:
                    self._data = json.load(f)
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(_STORE_FILE), exist_ok=True)
        with open(_STORE_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    # ─── Videos ──────────────────────────────────────────────────────────

    def save_video(self, video_id: str, data: dict):
        self._data["videos"][video_id] = {**data, "created_at": datetime.utcnow().isoformat()}
        self._save()

    def get_video(self, video_id: str) -> Optional[dict]:
        return self._data["videos"].get(video_id)

    def list_videos(self) -> List[dict]:
        return list(self._data["videos"].values())

    def update_video_status(self, video_id: str, status: str):
        if video_id in self._data["videos"]:
            self._data["videos"][video_id]["status"] = status
            self._save()

    # ─── Highlights ──────────────────────────────────────────────────────

    def save_highlight(self, highlight_id: str, data: dict):
        self._data["highlights"][highlight_id] = data
        self._save()

    def get_highlight(self, highlight_id: str) -> Optional[dict]:
        return self._data["highlights"].get(highlight_id)

    def get_highlights_for_video(self, video_id: str) -> List[dict]:
        return [h for h in self._data["highlights"].values() if h.get("video_id") == video_id]

    def list_highlights(self) -> List[dict]:
        return list(self._data["highlights"].values())

    # ─── Exports ─────────────────────────────────────────────────────────

    def save_export(self, job_id: str, data: dict):
        self._data["exports"][job_id] = data
        self._save()

    def get_export(self, job_id: str) -> Optional[dict]:
        return self._data["exports"].get(job_id)

    def list_exports(self) -> List[dict]:
        return list(self._data["exports"].values())

    # ─── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        videos = self.list_videos()
        highlights = self.list_highlights()
        scores = [h.get("virality_score", 0) for h in highlights]
        topics = [h.get("topic", "") for h in highlights if h.get("topic")]
        topic_counts = {}
        for t in topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        top_topics = sorted(topic_counts, key=topic_counts.get, reverse=True)[:5]

        return {
            "total_videos": len(videos),
            "total_clips": len(highlights),
            "avg_virality_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "top_topics": top_topics,
            "clips_by_format": {"reels": len(highlights), "shorts": len(highlights)},
        }


# Singleton
job_store = JobStore()
