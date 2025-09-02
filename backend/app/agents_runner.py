import os
import json
import asyncio
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import Client

from app.session_manager import SessionManager
from app.faiss_store import FAISSStore
from app.parsers.document_parser import DocumentParser
from app.agents import (
    IntakeAgent, AnalysisAgent, PSLAAgent, HearingPackAgent,
    ClientLetterAgent, DeclarationAgent, ResearchAgent, QualityGateAgent
)

class AgentsRunner:
    """Orchestrates the 8-agent pipeline for document analysis"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.faiss_store = FAISSStore()
        self.document_parser = DocumentParser()
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model="gpt-4",  # Will use gpt-5-nano when available
            temperature=0.1
        )
        
        # Initialize LangSmith
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY")
        ) if os.getenv("LANGSMITH_API_KEY") else None
        
        # Load prompt pack
        self.prompt_pack = self._load_prompt_pack()
        
        # Initialize agents
        self.agents = {
            "intake": IntakeAgent(self.llm, self.faiss_store),
            "analysis": AnalysisAgent(self.llm, self.faiss_store),
            "psla": PSLAAgent(self.llm, self.faiss_store),
            "hearing_pack": HearingPackAgent(self.llm),
            "client_letter": ClientLetterAgent(self.llm),
            "declaration": DeclarationAgent(self.llm),
            "research": ResearchAgent(self.llm),
            "quality_gate": QualityGateAgent(self.llm)
        }
    
    def _load_prompt_pack(self) -> List[Dict[str, Any]]:
        """Load prompt pack configuration"""
        prompt_pack_path = Path(__file__).parent.parent.parent / "agents" / "prompts" / "prompt_pack.json"
        with open(prompt_pack_path, 'r') as f:
            return json.load(f)
    
    async def run_intake_agent(self, session_id: str):
        """Run the intake agent - entry point of the pipeline"""
        try:
            await self.session_manager.update_session_status(
                session_id, "processing", "Running document intake analysis...", 
                current_stage="intake", progress=10
            )
            
            # Parse documents and create embeddings
            session = await self.session_manager.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Parse all uploaded documents
            parsed_docs = []
            for doc in session["uploaded_files"]:
                parsed_content = await self.document_parser.parse_document(doc["file_path"])
                parsed_docs.append({
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "content": parsed_content["text"],
                    "pages": parsed_content.get("pages", [])
                })
            
            # Create FAISS embeddings for session
            await self.faiss_store.create_session_index(session_id, parsed_docs)
            
            # Run intake agent
            intake_result = await self.agents["intake"].process(session_id, parsed_docs)
            
            # Save agent output
            await self.session_manager.save_agent_output(session_id, "intake", intake_result)
            
            # Check if clarifying questions are needed
            if intake_result.get("session_flags", {}).get("missing_critical_data"):
                await self._handle_clarifying_questions(session_id, intake_result)
            else:
                # Continue with pipeline
                await self.continue_pipeline(session_id)
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Intake analysis failed: {str(e)}"
            )
            self._log_error("intake", session_id, str(e))
    
    async def continue_pipeline(self, session_id: str):
        """Continue pipeline after intake (with or without clarifying questions)"""
        try:
            # Run Analysis and PSLA agents in parallel
            await self.session_manager.update_session_status(
                session_id, "processing", "Running pattern analysis...",
                current_stage="analysis", progress=30
            )
            
            # Get intake output
            session = await self.session_manager.get_session(session_id)
            intake_output = session["agent_outputs"]["intake"]
            
            # Run parallel analysis
            analysis_task = self.agents["analysis"].process(session_id, intake_output)
            psla_task = self.agents["psla"].process(session_id, intake_output)
            
            analysis_result, psla_result = await asyncio.gather(analysis_task, psla_task)
            
            # Save outputs
            await self.session_manager.save_agent_output(session_id, "analysis", analysis_result)
            await self.session_manager.save_agent_output(session_id, "psla", psla_result)
            
            # Continue with document generation
            await self._run_document_generation(session_id)
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Analysis failed: {str(e)}"
            )
            self._log_error("analysis", session_id, str(e))
    
    async def _run_document_generation(self, session_id: str):
        """Run hearing pack and declaration generation in parallel"""
        try:
            await self.session_manager.update_session_status(
                session_id, "processing", "Generating court documents...",
                current_stage="document_generation", progress=60
            )
            
            session = await self.session_manager.get_session(session_id)
            analysis_output = session["agent_outputs"]["analysis"]
            psla_output = session["agent_outputs"]["psla"]
            intake_output = session["agent_outputs"]["intake"]
            
            # Run parallel document generation
            hearing_pack_task = self.agents["hearing_pack"].process(
                session_id, intake_output, analysis_output, psla_output
            )
            declaration_task = self.agents["declaration"].process(
                session_id, intake_output, analysis_output
            )
            
            hearing_pack_result, declaration_result = await asyncio.gather(
                hearing_pack_task, declaration_task
            )
            
            # Save outputs
            await self.session_manager.save_agent_output(session_id, "hearing_pack", hearing_pack_result)
            await self.session_manager.save_agent_output(session_id, "declaration", declaration_result)
            
            # Continue with client materials
            await self._run_client_materials(session_id)
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Document generation failed: {str(e)}"
            )
            self._log_error("document_generation", session_id, str(e))
    
    async def _run_client_materials(self, session_id: str):
        """Generate client letter and research"""
        try:
            await self.session_manager.update_session_status(
                session_id, "processing", "Generating client materials...",
                current_stage="client_materials", progress=80
            )
            
            session = await self.session_manager.get_session(session_id)
            analysis_output = session["agent_outputs"]["analysis"]
            psla_output = session["agent_outputs"]["psla"]
            
            # Get jurisdiction from clarifying answers if available
            jurisdiction = session.get("clarifying_answers", {}).get("jurisdiction", "Unknown")
            
            # Run client letter and research
            client_letter_task = self.agents["client_letter"].process(
                session_id, analysis_output, psla_output, jurisdiction
            )
            research_task = self.agents["research"].process(session_id, jurisdiction)
            
            client_letter_result, research_result = await asyncio.gather(
                client_letter_task, research_task
            )
            
            # Save outputs
            await self.session_manager.save_agent_output(session_id, "client_letter", client_letter_result)
            await self.session_manager.save_agent_output(session_id, "research", research_result)
            
            # Run quality gate
            await self._run_quality_gate(session_id)
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Client materials generation failed: {str(e)}"
            )
            self._log_error("client_materials", session_id, str(e))
    
    async def _run_quality_gate(self, session_id: str):
        """Final quality check and completion"""
        try:
            await self.session_manager.update_session_status(
                session_id, "processing", "Running quality checks...",
                current_stage="quality_gate", progress=95
            )
            
            session = await self.session_manager.get_session(session_id)
            all_outputs = session["agent_outputs"]
            
            # Run quality gate
            quality_result = await self.agents["quality_gate"].process(session_id, all_outputs)
            
            # Save output
            await self.session_manager.save_agent_output(session_id, "quality_gate", quality_result)
            
            # Check if human review is required
            if quality_result.get("routing") == "require_human_review":
                await self.session_manager.update_session_status(
                    session_id, "requires_review", "Analysis complete. Human review recommended.",
                    progress=100, artifacts_ready=True
                )
            elif quality_result.get("routing") == "accept":
                await self.session_manager.update_session_status(
                    session_id, "completed", "Analysis complete. All artifacts ready for download.",
                    progress=100, artifacts_ready=True
                )
            else:
                await self.session_manager.update_session_status(
                    session_id, "requires_revision", "Analysis needs revision before completion.",
                    progress=90
                )
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Quality gate failed: {str(e)}"
            )
            self._log_error("quality_gate", session_id, str(e))
    
    async def _handle_clarifying_questions(self, session_id: str, intake_result: Dict[str, Any]):
        """Handle clarifying questions from intake"""
        missing_data = intake_result.get("session_flags", {}).get("missing_critical_data", [])
        
        questions = []
        for missing_item in missing_data[:3]:  # Max 3 questions
            if "jurisdiction" in missing_item.lower():
                questions.append({
                    "id": "jurisdiction",
                    "question": "What state or jurisdiction are these family law proceedings in?",
                    "type": "text",
                    "required": True
                })
            elif "child" in missing_item.lower() and "birth" in missing_item.lower():
                questions.append({
                    "id": "child_dob",
                    "question": "What are the birth dates of the children involved?",
                    "type": "text",
                    "required": True
                })
            elif "date" in missing_item.lower():
                questions.append({
                    "id": "case_date",
                    "question": "When did the legal proceedings begin?",
                    "type": "date",
                    "required": False
                })
        
        await self.session_manager.update_session_status(
            session_id, "waiting_input", "Need additional information to continue analysis",
            has_clarifying_questions=True, clarifying_questions=questions, progress=20
        )
    
    def _log_error(self, agent_id: str, session_id: str, error: str):
        """Log error to LangSmith if configured"""
        if self.langsmith_client:
            try:
                self.langsmith_client.create_run(
                    name=f"lance_ai_{agent_id}",
                    inputs={"session_id": session_id},
                    run_type="chain",
                    error=error,
                    project_name="lance-ai-prod"
                )
            except Exception:
                pass  # Don't fail on logging errors
    
    def _create_provenance(self, agent_id: str, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata for agent output"""
        return {
            "agent_id": agent_id,
            "model": "gpt-4",  # Will be gpt-5-nano when available
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
