"""
AttentionX AI — Main FastAPI Application
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.routes import upload, analyze, clips, captions, export, dashboard

load_dotenv()

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/clips", exist_ok=True)
os.makedirs("outputs/captions", exist_ok=True)
os.makedirs("outputs/exports", exist_ok=True)

app = FastAPI(
    title="AttentionX AI",
    description="Intelligent Content Repurposing Platform for Viral Micro-Content",
    version="1.0.0",
)

# CORS — allow all in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Routers
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(clips.router, prefix="/api/v1", tags=["Clips"])
app.include_router(captions.router, prefix="/api/v1", tags=["Captions"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])


@app.get("/")
async def root():
    return {
        "app": "AttentionX AI",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
