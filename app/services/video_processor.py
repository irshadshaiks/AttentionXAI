"""
Video Processor Service — handles video analysis, clipping, and vertical cropping
Uses MoviePy, OpenCV, MediaPipe, Librosa
"""
import os
import uuid
import json
import time
import math
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Lazy imports to avoid crash if optional deps missing
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


class VideoProcessor:
    """Core video processing engine."""

    def __init__(self, upload_dir: str = "uploads", output_dir: str = "outputs"):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.clips_dir = os.path.join(output_dir, "clips")
        self.exports_dir = os.path.join(output_dir, "exports")
        os.makedirs(self.clips_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)

    # ─── Video Metadata ─────────────────────────────────────────────────────

    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract basic metadata from video file."""
        meta = {
            "duration": 0,
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "file_size_mb": os.path.getsize(video_path) / (1024 * 1024),
        }

        if CV2_AVAILABLE:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                meta["fps"] = cap.get(cv2.CAP_PROP_FPS) or 30
                meta["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                meta["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                meta["duration"] = frame_count / meta["fps"] if meta["fps"] > 0 else 0
                cap.release()
        elif MOVIEPY_AVAILABLE:
            try:
                clip = VideoFileClip(video_path)
                meta["duration"] = clip.duration
                meta["fps"] = clip.fps
                meta["width"] = clip.w
                meta["height"] = clip.h
                clip.close()
            except Exception:
                pass

        return meta

    # ─── Audio Energy Detection ───────────────────────────────────────────

    def detect_audio_peaks(
        self, video_path: str, min_duration: float = 30, max_duration: float = 60
    ) -> List[Dict[str, Any]]:
        """
        Detect high-energy audio segments using Librosa.
        Falls back to simulated peaks if Librosa unavailable.
        """
        meta = self.get_video_metadata(video_path)
        total_duration = meta.get("duration", 300)
        
        # Adapt constraints for small videos
        if total_duration < min_duration:
            min_duration = max(5.0, total_duration * 0.5)
            max_duration = max(10.0, total_duration)

        if not LIBROSA_AVAILABLE:
            return self._simulate_peaks(video_path, min_duration, max_duration, total_duration)

        try:
            y, sr = librosa.load(video_path, sr=16000, mono=True)
        except Exception:
            return self._simulate_peaks(video_path, min_duration, max_duration, total_duration)

        # RMS energy with hop
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

        # Smooth and normalise with a 5-second window to ignore small pauses
        window = max(1, int(5.0 * sr / hop_length))
        smoothed = np.convolve(rms, np.ones(window) / window, mode="same")
        if smoothed.max() > 0:
            normalised = smoothed / smoothed.max()
        else:
            normalised = smoothed

        threshold = np.percentile(normalised, 50) if len(normalised) > 10 else 0
        peaks = []
        in_peak = False
        peak_start = 0.0

        for i, (t, val) in enumerate(zip(times, normalised)):
            if val >= threshold and not in_peak:
                in_peak = True
                peak_start = float(t)
            elif val < threshold and in_peak:
                peak_end = float(t)
                in_peak = False
                duration = peak_end - peak_start
                # Check min_duration, but be lenient for long videos
                if duration >= min_duration * 0.5:
                    actual_end = min(peak_start + max_duration, peak_end)
                    start_idx = max(0, i - int(duration * sr / hop_length))
                    avg_energy = float(np.mean(normalised[start_idx: i])) if i > start_idx else 0.5
                    peaks.append({
                        "start_time": round(peak_start, 2),
                        "end_time": round(actual_end, 2),
                        "energy_score": round(avg_energy * 100, 1),
                    })

        # Also grab final peak
        if in_peak:
            peak_end = float(times[-1])
            duration = peak_end - peak_start
            if duration >= min_duration:
                actual_end = min(peak_start + max_duration, peak_end)
                avg_energy = float(np.mean(normalised[-20:])) if len(normalised) >= 20 else 0.5
                peaks.append({
                    "start_time": round(peak_start, 2),
                    "end_time": round(actual_end, 2),
                    "energy_score": round(avg_energy * 100, 1),
                })
                
        # Provide absolute fallbacks just in case
        if not peaks:
            print("[VideoProcessor] No natural peaks found. Splitting video into chunks.")
            current_time = 0.0
            while current_time < total_duration:
                end = min(current_time + max_duration, total_duration)
                if end - current_time >= min_duration * 0.5:
                    peaks.append({
                        "start_time": round(current_time, 2),
                        "end_time": round(end, 2),
                        "energy_score": round(80.0, 1)
                    })
                current_time = end

        # Return top peaks by energy score
        peaks.sort(key=lambda x: x["energy_score"], reverse=True)
        return peaks[:10]  # max 10 peaks

    def _simulate_peaks(
        self, video_path: str, min_duration: float, max_duration: float, duration: float
    ) -> List[Dict[str, Any]]:
        """Generate realistic-looking simulated peaks when Librosa is unavailable."""
        num_peaks = min(8, max(3, int(duration / 60)))
        
        if duration < 60:
            num_peaks = 1
        
        peaks = []
        segment_len = duration / max(1, num_peaks)

        rng = np.random.default_rng(seed=42)
        for i in range(num_peaks):
            start = segment_len * (i + 0.5) if num_peaks > 1 else 0
            start = max(0, min(start, duration - min_duration))
            clip_dur = rng.uniform(min_duration, min(duration, max_duration))
            end = min(start + clip_dur, duration)
            energy = round(float(rng.uniform(55, 98)), 1)
            peaks.append({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "energy_score": energy,
            })

        return peaks

    # ─── Clip Extraction ─────────────────────────────────────────────────

    def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        clip_id: str,
        vertical: bool = True,
    ) -> str:
        """
        Extract a clip from start_time to end_time.
        Optionally crop to 9:16 vertical format.
        Returns path to output clip.
        """
        output_path = os.path.join(self.clips_dir, f"{clip_id}.mp4")

        if not MOVIEPY_AVAILABLE:
            # Create a placeholder file
            Path(output_path).write_text(f"placeholder:{start_time}-{end_time}")
            return output_path

        try:
            with VideoFileClip(video_path) as clip:
                subclip = clip.subclip(start_time, min(end_time, clip.duration))
                if vertical and clip.w > 0 and clip.h > 0:
                    subclip = self._crop_to_vertical(subclip)
                subclip.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    verbose=False,
                    logger=None,
                )
        except Exception as e:
            print(f"[VideoProcessor] clip extraction error: {e}")
            Path(output_path).write_text(f"error:{e}")

        return output_path

    def extract_audio_clip(self, video_path: str, start_time: float, end_time: float, clip_id: str) -> str:
        """Extract just the audio for a specific segment for faster API processing."""
        output_path = os.path.join(self.clips_dir, f"{clip_id}.mp3")
        if not MOVIEPY_AVAILABLE: return ""
        try:
            with VideoFileClip(video_path) as clip:
                subclip = clip.subclip(start_time, min(end_time, clip.duration))
                if subclip.audio:
                    subclip.audio.write_audiofile(output_path, logger=None, verbose=False)
                    return output_path
        except Exception:
            pass
        return ""

    def _crop_to_vertical(self, clip):
        """Crop 16:9 → 9:16 centred on faces if MediaPipe available, else centre crop."""
        target_aspect = 9 / 16
        current_aspect = clip.w / clip.h

        if current_aspect <= target_aspect:
            return clip  # already vertical-ish

        # Target width for 9:16
        target_w = int(clip.h * target_aspect)
        x_start = (clip.w - target_w) // 2

        if MP_AVAILABLE:
            face_x = self._detect_face_center(clip)
            if face_x is not None:
                x_start = max(0, min(face_x - target_w // 2, clip.w - target_w))

        return clip.crop(x1=x_start, x2=x_start + target_w)

    def _detect_face_center(self, clip) -> int:
        """Sample a few frames and return average face centre x-coordinate."""
        try:
            mp_face = mp.solutions.face_detection
            detector = mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5)

            sample_times = [clip.duration * t for t in [0.1, 0.3, 0.5, 0.7, 0.9]]
            xs = []

            for t in sample_times:
                frame = clip.get_frame(t)
                results = detector.process(frame)
                if results.detections:
                    for det in results.detections:
                        bb = det.location_data.relative_bounding_box
                        cx = int((bb.xmin + bb.width / 2) * clip.w)
                        xs.append(cx)

            detector.close()
            return int(np.mean(xs)) if xs else None
        except Exception:
            return None

    # ─── Thumbnail Generation ────────────────────────────────────────────

    def generate_thumbnail(self, video_path: str, time_sec: float, clip_id: str) -> str:
        """Extract a single frame as JPEG thumbnail."""
        thumb_dir = os.path.join(self.output_dir, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, f"{clip_id}.jpg")

        if CV2_AVAILABLE:
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
            ret, frame = cap.read()
            cap.release()
            if ret:
                cv2.imwrite(thumb_path, frame)
                return thumb_path
        elif MOVIEPY_AVAILABLE:
            try:
                with VideoFileClip(video_path) as clip:
                    clip.save_frame(thumb_path, t=min(time_sec, clip.duration - 0.1))
                    return thumb_path
            except Exception:
                pass

        return thumb_path


# Singleton
video_processor = VideoProcessor()
