import os
import shutil
from pathlib import Path
from typing import List
import asyncio
import logging

from app.session_manager import SessionManager
from app.faiss_store import FAISSStore

logger = logging.getLogger(__name__)

class PurgeService:
    """Handles session cleanup and data deletion"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.faiss_store = FAISSStore()
        self.upload_tmp_dir = Path(os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions"))
    
    async def purge_session(self, session_id: str) -> bool:
        """Complete purge of a specific session"""
        try:
            logger.info(f"Starting purge of session {session_id}")
            
            # 1. Get session data before deletion
            session = await self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for purge")
                return False
            
            # 2. Delete session files and directories
            session_dir = self.upload_tmp_dir / f"session_{session_id}"
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Deleted session directory: {session_dir}")
            
            # 3. Delete artifacts
            for artifact_name, artifact_path in session.get("artifacts", {}).items():
                artifact_file = Path(artifact_path)
                if artifact_file.exists():
                    artifact_file.unlink()
                    logger.info(f"Deleted artifact: {artifact_path}")
            
            # 4. Cleanup FAISS index
            self.faiss_store.cleanup_session(session_id)
            logger.info(f"Cleaned up FAISS index for session {session_id}")
            
            # 5. Delete session from database
            await self.session_manager.delete_session(session_id)
            logger.info(f"Deleted session from database: {session_id}")
            
            logger.info(f"Successfully purged session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to purge session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Cleanup all expired sessions"""
        try:
            expired_sessions = await self.session_manager.get_expired_sessions()
            
            if not expired_sessions:
                return 0
            
            logger.info(f"Found {len(expired_sessions)} expired sessions to cleanup")
            
            cleanup_count = 0
            for session_id in expired_sessions:
                try:
                    success = await self.purge_session(session_id)
                    if success:
                        cleanup_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup expired session {session_id}: {e}")
            
            logger.info(f"Successfully cleaned up {cleanup_count} expired sessions")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def cleanup_orphaned_files(self) -> int:
        """Clean up orphaned session directories without database entries"""
        try:
            if not self.upload_tmp_dir.exists():
                return 0
            
            cleanup_count = 0
            
            # Get all active session IDs from database
            # This is a simplified version - in production you'd want a more efficient query
            active_sessions = set()
            try:
                # We'll implement this when we have a method to get all active sessions
                # For now, we'll rely on TTL cleanup
                pass
            except Exception:
                pass
            
            # Find session directories
            for session_dir in self.upload_tmp_dir.glob("session_*"):
                if session_dir.is_dir():
                    session_id = session_dir.name.replace("session_", "")
                    
                    # Check if session still exists in database
                    session = await self.session_manager.get_session(session_id)
                    if not session:
                        try:
                            shutil.rmtree(session_dir)
                            # Also cleanup FAISS
                            self.faiss_store.cleanup_session(session_id)
                            cleanup_count += 1
                            logger.info(f"Cleaned up orphaned session directory: {session_dir}")
                        except Exception as e:
                            logger.error(f"Failed to cleanup orphaned directory {session_dir}: {e}")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned files: {e}")
            return 0
    
    async def get_storage_stats(self) -> dict:
        """Get storage usage statistics"""
        try:
            stats = {
                "total_sessions": 0,
                "total_size_bytes": 0,
                "session_directories": 0,
                "faiss_indexes": 0
            }
            
            if not self.upload_tmp_dir.exists():
                return stats
            
            # Count session directories and calculate size
            for session_dir in self.upload_tmp_dir.glob("session_*"):
                if session_dir.is_dir():
                    stats["session_directories"] += 1
                    
                    # Calculate directory size
                    for file_path in session_dir.rglob("*"):
                        if file_path.is_file():
                            stats["total_size_bytes"] += file_path.stat().st_size
            
            # Count FAISS indexes
            faiss_dir = Path(os.getenv("FAISS_DATA_DIR", "/tmp/faiss"))
            if faiss_dir.exists():
                for faiss_file in faiss_dir.glob("session_*.index"):
                    stats["faiss_indexes"] += 1
                    stats["total_size_bytes"] += faiss_file.stat().st_size
                
                for metadata_file in faiss_dir.glob("session_*.metadata"):
                    stats["total_size_bytes"] += metadata_file.stat().st_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}
    
    async def emergency_cleanup(self) -> dict:
        """Emergency cleanup of all temporary data"""
        logger.warning("Starting emergency cleanup of all temporary data")
        
        results = {
            "session_dirs_removed": 0,
            "faiss_files_removed": 0,
            "database_cleared": False,
            "errors": []
        }
        
        try:
            # Remove all session directories
            if self.upload_tmp_dir.exists():
                for session_dir in self.upload_tmp_dir.glob("session_*"):
                    try:
                        shutil.rmtree(session_dir)
                        results["session_dirs_removed"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed to remove {session_dir}: {e}")
            
            # Remove all FAISS files
            faiss_dir = Path(os.getenv("FAISS_DATA_DIR", "/tmp/faiss"))
            if faiss_dir.exists():
                for faiss_file in faiss_dir.glob("session_*.*"):
                    try:
                        faiss_file.unlink()
                        results["faiss_files_removed"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed to remove {faiss_file}: {e}")
            
            # Clear session database (recreate empty)
            try:
                db_path = os.getenv("DB_PATH", "sqlite:///tmp/lance/sessions.sqlite")
                if db_path.startswith("sqlite://"):
                    db_path = db_path[9:]
                
                if Path(db_path).exists():
                    Path(db_path).unlink()
                
                # Reinitialize database
                await self.session_manager.initialize()
                results["database_cleared"] = True
                
            except Exception as e:
                results["errors"].append(f"Failed to clear database: {e}")
            
            logger.warning(f"Emergency cleanup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
            results["errors"].append(f"Emergency cleanup failed: {e}")
            return results
