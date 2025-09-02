import os
import json
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.models import SessionData, DocumentInfo

class SessionManager:
    """Manages ephemeral session storage in SQLite"""
    
    def __init__(self):
        self.db_path = os.getenv("DB_PATH", "sqlite:///tmp/lance/sessions.sqlite")
        if self.db_path.startswith("sqlite://"):
            self.db_path = self.db_path[9:]  # Remove sqlite:// prefix
        self.session_ttl = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
        
    async def initialize(self):
        """Initialize database tables"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    data TEXT NOT NULL  -- JSON blob
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)
            """)
            await db.commit()
    
    async def create_session(self, session_id: str, uploaded_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create new session with uploaded files"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.session_ttl)
        
        # Convert uploaded files to DocumentInfo objects
        documents = []
        for file_info in uploaded_files:
            doc_info = DocumentInfo(
                doc_id=f"doc_{len(documents) + 1}",
                filename=file_info["filename"],
                file_path=file_info["path"],
                size=file_info["size"],
                type=self._get_file_type(file_info["filename"])
            )
            documents.append(doc_info)
        
        session_data = SessionData(
            session_id=session_id,
            status="created",
            created_at=now,
            expires_at=expires_at,
            uploaded_files=documents,
            message="Session created with uploaded files"
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (session_id, status, created_at, expires_at, data) VALUES (?, ?, ?, ?, ?)",
                (session_id, "created", now.isoformat(), expires_at.isoformat(), session_data.model_dump_json())
            )
            await db.commit()
        
        return session_data.model_dump()
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM sessions WHERE session_id = ? AND expires_at > ?",
                (session_id, datetime.utcnow().isoformat())
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None
    
    async def update_session_status(self, session_id: str, status: str, message: str = "", **kwargs):
        """Update session status and other fields"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Update fields
        session["status"] = status
        session["message"] = message
        
        # Update additional fields if provided
        for key, value in kwargs.items():
            if key in session:
                session[key] = value
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET status = ?, data = ? WHERE session_id = ?",
                (status, json.dumps(session), session_id)
            )
            await db.commit()
        return True
    
    async def save_clarifying_answers(self, session_id: str, answers: Dict[str, str]):
        """Save answers to clarifying questions"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["clarifying_answers"] = answers
        session["has_clarifying_questions"] = False
        session["status"] = "processing"
        session["message"] = "Received clarifying answers, continuing analysis..."
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET data = ? WHERE session_id = ?",
                (json.dumps(session), session_id)
            )
            await db.commit()
        return True
    
    async def save_agent_output(self, session_id: str, agent_id: str, output: Dict[str, Any]):
        """Save output from an agent"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["agent_outputs"][agent_id] = output
        
        # Update completed stages
        if agent_id not in session["completed_stages"]:
            session["completed_stages"].append(agent_id)
        
        # Update progress based on completed stages
        total_stages = 8  # 8 agents in pipeline
        session["progress"] = int((len(session["completed_stages"]) / total_stages) * 100)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET data = ? WHERE session_id = ?",
                (json.dumps(session), session_id)
            )
            await db.commit()
        return True
    
    async def save_artifact(self, session_id: str, artifact_name: str, file_path: str):
        """Save artifact file path to session"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["artifacts"][artifact_name] = file_path
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET data = ? WHERE session_id = ?",
                (json.dumps(session), session_id)
            )
            await db.commit()
        return True
    
    async def get_session_artifacts(self, session_id: str) -> List[Dict[str, str]]:
        """Get list of available artifacts"""
        session = await self.get_session(session_id)
        if not session:
            return []
        
        artifacts = []
        for artifact_name, file_path in session.get("artifacts", {}).items():
            if Path(file_path).exists():
                artifacts.append({
                    "name": artifact_name,
                    "size": Path(file_path).stat().st_size,
                    "created": datetime.fromtimestamp(Path(file_path).stat().st_mtime).isoformat()
                })
        
        return artifacts
    
    async def get_artifact_path(self, session_id: str, artifact_name: str) -> Optional[str]:
        """Get file path for specific artifact"""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return session.get("artifacts", {}).get(artifact_name)
    
    async def get_expired_sessions(self) -> List[str]:
        """Get list of expired session IDs"""
        expired_sessions = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT session_id FROM sessions WHERE expires_at <= ?",
                (datetime.utcnow().isoformat(),)
            ) as cursor:
                async for row in cursor:
                    expired_sessions.append(row[0])
        return expired_sessions
    
    async def delete_session(self, session_id: str):
        """Delete session from database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        extension = Path(filename).suffix.lower()
        if extension == '.pdf':
            return 'pdf'
        elif extension in ['.doc', '.docx']:
            return 'document'
        elif extension in ['.txt']:
            return 'text'
        elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return 'image'
        else:
            return 'unknown'
