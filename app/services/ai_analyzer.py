"""
AI Analyzer Service — uses Gemini 1.5 Flash for sentiment, hooks, and virality scoring.
Falls back to deterministic heuristics when API not available.
"""
import os
import json
import math
import random
import hashlib
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

TOPICS = [
    "Mindset & Growth", "Success Habits", "Entrepreneurship", "Leadership",
    "Mental Health", "Productivity", "Finance", "Relationships", "Motivation",
    "Personal Branding", "Marketing Strategy", "AI & Technology", "Life Advice",
]

HOOK_TEMPLATES = [
    "This will completely change how you think about {topic} 🔥",
    "Nobody talks about this {topic} secret…",
    "The {topic} truth no one tells you 👀",
    "Stop making this {topic} mistake immediately ⚠️",
    "{topic} hack that 99% of people don't know 🤯",
    "I tried {topic} for 30 days — here's what happened",
    "The #1 {topic} lesson that changed my life 💡",
    "Why most people fail at {topic} (and how to fix it)",
    "This {topic} strategy made me 10x more effective ⚡",
    "The uncomfortable truth about {topic} 🎯",
]


class AIAnalyzer:
    """Gemini-powered AI analysis with deterministic fallback."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = None

        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                print(f"[AIAnalyzer] Gemini init failed: {e}")

    # ─── Public API ──────────────────────────────────────────────────────

    def analyze_segment(
        self,
        video_id: str,
        transcript_snippet: str,
        energy_score: float,
        start_time: float,
        end_time: float,
        audio_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Full segment analysis: topic, sentiment, hook, virality, transcript."""
        if self.model and (transcript_snippet or audio_path):
            return self._gemini_analyze(transcript_snippet, energy_score, audio_path)
        return self._heuristic_analyze(video_id, energy_score, start_time)

    def generate_hook(self, topic: str, transcript: Optional[str] = None) -> str:
        """Generate a viral hook title."""
        if self.model and transcript:
            return self._gemini_hook(topic, transcript)
        return self._template_hook(topic)

    def predict_virality(
        self,
        energy_score: float,
        sentiment_score: float,
        topic: str,
        duration: float,
    ) -> float:
        """Predict virality score 0–100."""
        # Multi-factor virality model
        energy_w = energy_score * 0.35
        sentiment_w = sentiment_score * 0.25
        duration_score = 100 * (1 - abs(45 - duration) / 45)  # peak at 45s
        duration_w = max(0, duration_score) * 0.20
        topic_bonus = self._topic_trend_score(topic) * 0.20

        raw = energy_w + sentiment_w + duration_w + topic_bonus
        # Add small noise for variety
        seed = int(energy_score * 1000) % 100
        noise = (seed % 10 - 5)
        return round(min(99, max(10, raw + noise)), 1)

    # ─── Gemini Calls ────────────────────────────────────────────────────

    def _gemini_analyze(self, transcript: str, energy_score: float, audio_path: Optional[str] = None) -> Dict[str, Any]:
        prompt = f"""You are an expert viral content analyst.

Analyze this short audio/video segment and respond ONLY with a JSON object containing:
- topic: (one of: Mindset & Growth, Success Habits, Entrepreneurship, Leadership, Mental Health, Productivity, Finance, Relationships, Motivation, Personal Branding, Marketing Strategy, AI & Technology, Life Advice)
- description: brief 1-sentence description of the segment
- sentiment_score: emotional positivity/intensity 0-100
- hook_title: a viral, engaging short title under 15 words with an emoji
- key_insight: the most shareable quote or idea
- transcript: writing out exactly what was spoken in the audio. If no audio was provided, make an educated guess of a powerful quote.

Energy score of this segment: {energy_score}
"""
        try:
            contents = [prompt]
            uploaded_file = None
            if audio_path and os.path.exists(audio_path):
                uploaded_file = genai.upload_file(audio_path)
                contents.insert(0, uploaded_file)
            elif transcript:
                contents.append(f'\nTranscript: "{transcript[:800]}"')

            response = self.model.generate_content(contents)
            
            # Clean up the file from google's servers if we uploaded one
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception as cleanup_err:
                    print(f"Failed to clean up gemini file: {cleanup_err}")

            text = response.text.strip()
            if text.startswith("```"):
                text = text[text.index("{"):text.rindex("}") + 1]
            return json.loads(text)
        except Exception as e:
            print(f"[AIAnalyzer] Gemini analyze error: {e}")
            return {}

    def _gemini_hook(self, topic: str, transcript: str) -> str:
        prompt = f"""Create one viral, scroll-stopping social media hook title for this content.
Topic: {topic}
Content snippet: "{transcript[:300]}"

Rules:
- Under 12 words
- Include one relevant emoji
- Create curiosity or urgency
- Don't use clickbait — make it authentic

Return ONLY the hook title, nothing else."""
        try:
            return self.model.generate_content(prompt).text.strip()
        except Exception:
            return self._template_hook(topic)

    # ─── Fallback Heuristics ─────────────────────────────────────────────

    def _heuristic_analyze(
        self, video_id: str, energy_score: float, start_time: float
    ) -> Dict[str, Any]:
        # Deterministic but varied based on inputs
        seed = int(hashlib.md5(f"{video_id}{start_time}".encode()).hexdigest(), 16)
        rng = random.Random(seed)
        topic = rng.choice(TOPICS)
        sentiment = round(rng.uniform(60, 95), 1)
        return {
            "topic": topic,
            "description": f"High-energy segment about {topic.lower()} with strong audience appeal.",
            "sentiment_score": sentiment,
            "hook_title": self._template_hook(topic, rng),
            "key_insight": f"Key insight about {topic.lower()} revealed in this segment.",
        }

    def _template_hook(self, topic: str, rng: random.Random = None) -> str:
        if rng is None:
            rng = random.Random(hash(topic))
        template = rng.choice(HOOK_TEMPLATES)
        return template.replace("{topic}", topic.lower())

    def _topic_trend_score(self, topic: str) -> float:
        """Simulate trend scores for topics."""
        scores = {
            "AI & Technology": 95, "Entrepreneurship": 88, "Mindset & Growth": 85,
            "Personal Branding": 82, "Productivity": 80, "Finance": 78,
            "Mental Health": 75, "Marketing Strategy": 73, "Success Habits": 70,
            "Leadership": 68, "Motivation": 65, "Relationships": 62, "Life Advice": 60,
        }
        return scores.get(topic, 65)


# Singleton
ai_analyzer = AIAnalyzer()
