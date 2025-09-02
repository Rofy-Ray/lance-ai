import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.models import SessionCreate, SessionResponse, SessionStatus, SessionDelete
from app.session_manager import SessionManager
from app.agents_runner import AgentsRunner
from app.parsers.document_parser import DocumentParser
from app.purge import PurgeService

# Initialize FastAPI app
app = FastAPI(
    title="Lance AI API",
    description="Privacy-first AI analysis for post-separation abuse detection",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
session_manager = SessionManager()
agents_runner = AgentsRunner()
document_parser = DocumentParser()
purge_service = PurgeService()

# Constants
UPLOAD_TMP_DIR = os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)
    await session_manager.initialize()
    # Start TTL cleanup task
    asyncio.create_task(ttl_cleanup_task())

async def ttl_cleanup_task():
    """Background task to clean up expired sessions"""
    while True:
        try:
            await purge_service.cleanup_expired_sessions()
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            print(f"TTL cleanup error: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error

@app.get("/api/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/upload", response_model=SessionResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload files and create new session"""
    try:
        session_id = str(uuid.uuid4())
        session_dir = Path(UPLOAD_TMP_DIR) / f"session_{session_id}"
        uploads_dir = session_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        
        # Save uploaded files
        for file in files:
            if not file.filename:
                continue
                
            file_path = uploads_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
        
        if not uploaded_files:
            raise HTTPException(status_code=400, detail="No valid files uploaded")
        
        # Create session
        session_data = await session_manager.create_session(
            session_id=session_id,
            uploaded_files=uploaded_files
        )
        
        return SessionResponse(
            session_id=session_id,
            status="created",
            uploaded_files=len(uploaded_files),
            message="Files uploaded successfully. Ready to start analysis."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/session/{session_id}/start")
async def start_analysis(session_id: str, background_tasks: BackgroundTasks):
    """Trigger intake agent and start analysis pipeline"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Start intake agent in background
        background_tasks.add_task(agents_runner.run_intake_agent, session_id)
        
        # Update session status
        await session_manager.update_session_status(session_id, "processing", "Starting document intake analysis...")
        
        return {"status": "started", "message": "Analysis pipeline initiated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.post("/api/session/{session_id}/answer")
async def answer_clarifying_questions(
    session_id: str,
    answers: Dict[str, str],
    background_tasks: BackgroundTasks
):
    """Accept answers to clarifying questions and continue pipeline"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Save answers to session
        await session_manager.save_clarifying_answers(session_id, answers)
        
        # Continue with analysis pipeline
        background_tasks.add_task(agents_runner.continue_pipeline, session_id)
        
        return {"status": "answers_received", "message": "Continuing analysis with provided information"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answers: {str(e)}")

@app.get("/api/session/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """Get current session status (non-PII only)"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionStatus(
            session_id=session_id,
            status=session["status"],
            progress=session.get("progress", 0),
            current_stage=session.get("current_stage", ""),
            message=session.get("message", ""),
            has_clarifying_questions=session.get("has_clarifying_questions", False),
            clarifying_questions=session.get("clarifying_questions", []),
            completed_stages=session.get("completed_stages", []),
            artifacts_ready=session.get("artifacts_ready", False),
            created_at=session["created_at"],
            expires_at=session["expires_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/api/session/{session_id}/artifacts")
async def list_artifacts(session_id: str):
    """List available artifacts for download"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        artifacts = await session_manager.get_session_artifacts(session_id)
        
        return {
            "session_id": session_id,
            "artifacts": artifacts,
            "download_base_url": f"/api/session/{session_id}/download"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list artifacts: {str(e)}")

@app.get("/api/session/{session_id}/download/{artifact_name}")
async def download_artifact(session_id: str, artifact_name: str):
    """Download specific artifact"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        artifact_path = await session_manager.get_artifact_path(session_id, artifact_name)
        if not artifact_path or not Path(artifact_path).exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        return FileResponse(
            path=artifact_path,
            filename=artifact_name,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download artifact: {str(e)}")

@app.post("/api/session/{session_id}/delete")
async def delete_session(session_id: str, delete_request: SessionDelete):
    """Manual session deletion with confirmation"""
    try:
        if not delete_request.confirm:
            raise HTTPException(status_code=400, detail="Deletion not confirmed")
        
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Execute purge routine
        await purge_service.purge_session(session_id)
        
        return {"status": "deleted", "message": "Session and all data permanently deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
