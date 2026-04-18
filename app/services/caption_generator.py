"""
Caption Generator Service — Whisper speech-to-text + word-level timing.
Falls back to placeholder captions when Whisper unavailable.
"""
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")


class CaptionGenerator:
    """Generates word-by-word timed captions using OpenAI Whisper."""

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None and WHISPER_AVAILABLE:
            try:
                self._model = whisper.load_model(WHISPER_MODEL_SIZE)
                print(f"[CaptionGenerator] Whisper {WHISPER_MODEL_SIZE} loaded.")
            except Exception as e:
                print(f"[CaptionGenerator] Whisper load failed: {e}")
        return self._model

    # ─── Public API ──────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        word_timestamps: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe audio and return full transcript + word timings.
        Returns:
            {text, segments: [{start, end, text, words: [{word, start, end}]}]}
        """
        model = self._load_model()
        if model is None:
            return self._placeholder_transcript(audio_path)

        try:
            result = model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                word_timestamps=word_timestamps,
                verbose=False,
            )
            return result
        except Exception as e:
            print(f"[CaptionGenerator] transcription error: {e}")
            return self._placeholder_transcript(audio_path)

    def generate_captions(
        self, audio_path: str, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Return list of caption chunks suitable for SRT/overlay.
        Each chunk: {start, end, text, words}
        """
        result = self.transcribe(audio_path, language=language)
        captions = []

        for segment in result.get("segments", []):
            captions.append({
                "start": round(segment["start"], 3),
                "end": round(segment["end"], 3),
                "text": segment["text"].strip(),
                "words": [
                    {
                        "word": w.get("word", "").strip(),
                        "start": round(w.get("start", segment["start"]), 3),
                        "end": round(w.get("end", segment["end"]), 3),
                    }
                    for w in segment.get("words", [])
                ],
            })

        return captions

    def to_srt(self, captions: List[Dict[str, Any]]) -> str:
        """Convert captions list to SRT format string."""
        srt_lines = []
        for i, cap in enumerate(captions, 1):
            start = self._seconds_to_srt_time(cap["start"])
            end = self._seconds_to_srt_time(cap["end"])
            srt_lines.append(f"{i}\n{start} --> {end}\n{cap['text']}\n")
        return "\n".join(srt_lines)

    def save_srt(self, captions: List[Dict[str, Any]], output_path: str) -> str:
        """Write SRT file and return path."""
        srt = self.to_srt(captions)
        Path(output_path).write_text(srt, encoding="utf-8")
        return output_path

    # ─── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    @staticmethod
    def _placeholder_transcript(audio_path: str) -> Dict[str, Any]:
        """Generate placeholder transcript when Whisper unavailable."""
        sample_texts = [
            "The most important thing is to keep moving forward no matter what.",
            "Success is not about luck it's about consistency and showing up every day.",
            "Your mindset determines your reality more than any external factor.",
            "The people who win are the ones who never stop learning and growing.",
            "Focus on what you can control and let go of everything else.",
            "Every setback is a setup for a comeback.",
        ]
        segments = []
        t = 0.0
        for i, text in enumerate(sample_texts):
            words = text.split()
            word_dur = 0.4
            dur = len(words) * word_dur
            word_objs = [
                {"word": w, "start": round(t + j * word_dur, 3), "end": round(t + (j + 1) * word_dur, 3)}
                for j, w in enumerate(words)
            ]
            segments.append({
                "start": round(t, 3),
                "end": round(t + dur, 3),
                "text": text,
                "words": word_objs,
            })
            t += dur + 0.3

        return {"text": " ".join(sample_texts), "segments": segments}


# Singleton
caption_generator = CaptionGenerator()
