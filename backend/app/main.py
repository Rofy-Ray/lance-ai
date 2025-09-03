import os
import uuid
import asyncio
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import logging
import tempfile
from dotenv import load_dotenv
from pydantic import BaseModel
import json
import shutil
from uvicorn import Config, Server

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    # Calculate cleanup interval as 10% of session TTL, with reasonable bounds
    cleanup_interval = max(60, min(SESSION_TTL_SECONDS // 10, 600))  # Between 1-10 minutes
    error_retry_interval = max(30, cleanup_interval // 10)  # 10% of cleanup interval for errors
    
    logger.info(f"Starting TTL cleanup task: checking every {cleanup_interval}s (TTL: {SESSION_TTL_SECONDS}s)")
    
    while True:
        try:
            await purge_service.cleanup_expired_sessions()
            await asyncio.sleep(cleanup_interval)
        except Exception as e:
            logger.error(f"TTL cleanup error: {e}")
            await asyncio.sleep(error_retry_interval)

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
    logger.info(f"Starting analysis for session {session_id}")
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found when trying to start analysis")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Session {session_id}: Adding intake agent task to background")
        # Start intake agent in background
        background_tasks.add_task(agents_runner.run_intake_agent, session_id)
        
        # Update session status
        await session_manager.update_session_status(session_id, "processing", "Starting document intake analysis...")
        logger.info(f"Session {session_id}: Analysis pipeline initiated successfully")
        
        return {"status": "started", "message": "Analysis pipeline initiated"}
        
    except Exception as e:
        logger.error(f"Failed to start analysis for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.post("/api/session/{session_id}/answer")
async def answer_clarifying_questions(
    session_id: str,
    request_body: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Accept answers to clarifying questions and continue pipeline"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Extract answers from request body
        answers = request_body.get('answers', {})
        
        # Save answers to session
        await session_manager.save_clarifying_answers(session_id, answers)
        
        # Continue with analysis pipeline via agents_runner method
        background_tasks.add_task(agents_runner.process_clarifying_answers, session_id, answers)
        
        return {"status": "answers_received", "message": "Continuing analysis with provided information"}
        
    except Exception as e:
        logger.error(f"Failed to process clarifying answers for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process answers: {str(e)}")

@app.get("/api/session/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """Get current session status (non-PII only)"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Log the full session data to debug missing fields
        logger.info(f"Session {session_id} status data keys: {list(session.keys())}")
        
        # Safely extract clarifying questions with proper fallbacks
        clarifying_questions = session.get("clarifying_questions", [])
        pending_questions = session.get("pending_questions", [])
        
        # Ensure questions are in correct format
        if not isinstance(clarifying_questions, list):
            clarifying_questions = []
        if not isinstance(pending_questions, list):
            pending_questions = []
            
        return SessionStatus(
            session_id=session_id,
            status=session["status"],
            progress=session.get("progress", 0),
            current_stage=session.get("current_stage", ""),
            current_step=session.get("current_step", ""),
            step_progress=session.get("step_progress", 0),
            step_start_time=session.get("step_start_time"),
            estimated_completion_time=session.get("estimated_completion_time"),
            detailed_status_message=session.get("detailed_status_message", ""),
            message=session.get("message", ""),
            has_clarifying_questions=session.get("has_clarifying_questions", False),
            clarifying_questions=clarifying_questions,
            pending_questions=pending_questions,
            completed_stages=session.get("completed_stages", []),
            failed_stages=session.get("failed_stages", []),
            artifacts_available=session.get("artifacts_available", []),
            artifacts_ready=session.get("artifacts_ready", False),
            created_at=session["created_at"],
            expires_at=session["expires_at"]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting session status for {session_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/api/session/{session_id}/artifacts")
async def get_session_artifacts(session_id: str):
    """Get available artifacts for session"""
    try:
        artifacts = await session_manager.get_session_artifacts(session_id)
        return {
            "session_id": session_id,
            "artifacts": artifacts,
            "download_base_url": f"/api/session/{session_id}/download/"
        }
    except Exception as e:
        logger.error(f"Failed to get artifacts for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve artifacts")

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

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session endpoint matching frontend expectations"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            # Return success even if session not found (idempotent deletion)
            return {"status": "deleted", "message": "Session not found or already deleted"}
        
        # Execute purge routine
        await purge_service.purge_session(session_id)
        
        return {"status": "deleted", "message": "Session and all data permanently deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@app.post("/api/session/{session_id}/delete")
async def delete_session_with_confirmation(session_id: str, delete_request: SessionDelete):
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
