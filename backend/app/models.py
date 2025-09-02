from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

class SessionCreate(BaseModel):
    files: List[str]

class SessionResponse(BaseModel):
    session_id: str
    status: str
    uploaded_files: int
    message: str

class SessionStatus(BaseModel):
    session_id: str
    status: str  # created, processing, waiting_input, completed, error, expired
    progress: int  # 0-100
    current_stage: str
    message: str
    has_clarifying_questions: bool = False
    clarifying_questions: List[Dict[str, Any]] = []
    pending_questions: List[Dict[str, Any]] = []
    completed_stages: List[str] = []
    failed_stages: List[str] = []
    artifacts_ready: bool = False
    created_at: datetime
    expires_at: datetime
    current_step: str = ""
    step_progress: int = 0  # 0-100 for current step
    step_start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    detailed_status_message: str = ""
    artifacts_available: List[str] = []

class SessionDelete(BaseModel):
    confirm: bool

class ClarifyingAnswer(BaseModel):
    question_id: str
    answer: str

class AgentOutput(BaseModel):
    agent_id: str
    session_id: str
    status: str  # success, error, needs_input
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provenance: Dict[str, Any]

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_path: str
    size: int
    type: str
    parsed: bool = False
    text_content: Optional[str] = None
    page_count: Optional[int] = None

class SessionData(BaseModel):
    session_id: str
    status: str
    created_at: datetime
    expires_at: datetime
    uploaded_files: List[DocumentInfo]
    progress: int = 0
    current_stage: str = ""
    message: str = ""
    has_clarifying_questions: bool = False
    clarifying_questions: List[Dict[str, Any]] = []
    clarifying_answers: Dict[str, str] = {}
    completed_stages: List[str] = []
    failed_stages: List[str] = []
    artifacts: Dict[str, str] = {}  # artifact_name -> file_path
    agent_outputs: Dict[str, Dict[str, Any]] = {}  # agent_id -> output
    artifacts_ready: bool = False
    current_step: str = ""
    step_progress: int = 0
    step_start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    detailed_status_message: str = ""
    artifacts_available: List[str] = []
