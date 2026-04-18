<div align="center">
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Gemini-Dark.svg" height="80" alt="Gemini" />
  <h1>⚡ AttentionX AI</h1>
  <p><strong>Intelligent Content Repurposing Platform for Viral Micro-Content</strong></p>
  
  <p>
    <a href="#features">Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#architecture">Architecture</a>
  </p>
</div>

---

## 🎯 The Problem

Modern mentors, educators, and creators produce long-form video content (30–90 mins), but today's audience prefers short-form, engaging, vertical content (Reels, Shorts, TikTok). High-value insights are buried deep inside long videos, and manual editing is tedious and non-scalable.

## 💡 The Solution: AttentionX AI

AttentionX AI is a fully automated platform that transforms long videos into viral-ready short clips using GenAI + Multimodal AI + Video Processing.

Upload a 1-hour masterclass, and in minutes, AttentionX will:
1. Scan the audio and transcript for emotional peaks and high energy.
2. Select the most engaging 30–60 second segments.
3. Automatically crop the video to a vertical 9:16 format keeping the speaker centered.
4. Generate dynamic, word-by-word karaoke-style captions.
5. Create scroll-stopping "hook" titles using Gemini.

---

## 🔥 Features

### Core Capabilities
* **🎥 Smart Video Upload:** Drag-and-drop support for MP4, MOV, and AVI up to 500MB.
* **🧠 Emotional Peak Detection:** Analyzes audio intensity (Librosa) and speech sentiment (Gemini) to identify the highest-impact moments.
* **✂️ Automated Clip Generation:** Automatically extracts clips and scores them by virality potential.
* **📱 Smart Vertical Cropping:** Uses MediaPipe face tracking to crop 16:9 videos into 9:16 vertical clips, ensuring the speaker is never out of frame.
* **📝 Karaoke Captions:** Whisper integration for accurate, word-by-word timed captions with multiple themes (Netflix, YouTube, TikTok).
* **🎯 Viral Hook Generator:** Gemini crafts compelling hook titles tailored to the clip's topic.
* **🚀 One-Click Export:** Download directly in Reels, Shorts, or TikTok formats.

### Winning Edge / Analytics
* **🔥 Virality Score AI:** Predicts engagement based on energy, sentiment, topic trends, and length.
* **📊 Analytics Dashboard:** Track processed videos, generated clips, top topics, and average virality scores.

---

## 🏗️ Tech Stack

### Backend
* **Python & FastAPI**: For a high-performance, asynchronous REST API.
* **Google Gemini 1.5 Flash**: For hook generation, sentiment analysis, and topic extraction.
* **OpenAI Whisper**: High-accuracy local speech-to-text generation.
* **MoviePy & OpenCV**: For fast video slicing, formatting, and thumbnail generation.
* **Librosa**: For deep audio energy peak detection.
* **MediaPipe**: For facial tracking to automate smart vertical framing.

### Frontend
* **Vanilla JS, HTML, CSS**: Built for maximum performance without build-step overhead.
* **Glassmorphic UI**: High-end premium dark mode design with CSS gradients and transitions.
* **Apple-level Simplicity**: Highly polished user experience inspired by CapCut and Canva.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* FFmpeg installed on your system (`brew install ffmpeg` / `apt-get install ffmpeg`)
* A Gemini API Key from Google AI Studio.

### Installation

1. **Clone the repository and enter the backend directory**
   ```bash
   cd backend
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the `backend` directory (copying `.env.example`):
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   UPLOAD_DIR=uploads
   OUTPUT_DIR=outputs
   MAX_FILE_SIZE_MB=500
   ```

### Running the Platform

To launch the full stack locally:

**1. Start the FastAPI Backend**
```bash
cd backend
uvicorn main:app --reload --port 8000
```
*The API handles requests on `http://localhost:8000`*
*The API Documentation is available at `http://localhost:8000/docs`*

**2. Open the Frontend**
Since the frontend is built entirely with optimized static files, you only need to open the `index.html` file in your browser, or serve it directly:
```bash
cd frontend
python -m http.server 3000
```
Then visit `http://localhost:3000` in your web browser!

> **Demo Mode:** If you do not provide valid API keys, or if you run the frontend without the backend active, AttentionX AI will gracefully fallback into an interactive Demo Mode showcasing simulated upload, analysis, and processing flows.

---

## 🧩 Architecture Flow

1. **User Action:** User drags/drops video on the frontend UI.
2. **Upload Manager:** FastAPI streams the upload to disk (`/api/v1/upload`).
3. **Trigger Analysis:** User begins AI analysis (`/api/v1/analyze`).
4. **Phase 1 (Audio):** Librosa scans the video's audio track for volume spikes and energy changes.
5. **Phase 2 (Content):** Whisper transcribes these high-energy segments.
6. **Phase 3 (Emotion/Hook):** Gemini processes the transcripts to evaluate sentiment, score the "Virality" factor, classify the topic, and generate a scroll-stopping textual Hook.
7. **Phase 4 (Video Slicing):** MoviePy creates the subclip. MediaPipe tracks the speaker's face to apply an intelligent 9:16 center-crop for mobile.
8. **Export:** User customizes caption themes and exports the final `.mp4` optimized for TikTok/Reels/Shorts.

---

<div align="center">
  <p>Built for the 2026 AI Hackathon</p>
</div>
