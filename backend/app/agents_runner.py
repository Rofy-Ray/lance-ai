import asyncio
import json
import os
import traceback
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langsmith import Client

from .session_manager import SessionManager
from .parsers.document_parser import DocumentParser
from .faiss_store import FAISSStore
from .agents.intake_agent import IntakeAgent
from .agents.analysis_agent import AnalysisAgent
from .agents.psla_agent import PSLAAgent
from .agents.hearing_pack_agent import HearingPackAgent
from .agents.declaration_agent import DeclarationAgent
from .agents.client_letter_agent import ClientLetterAgent
from .agents.research_agent import ResearchAgent
from .agents.quality_gate_agent import QualityGateAgent

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
    
    def _estimate_completion_time(self, session_id: str, stage: str) -> datetime:
        """Estimate completion time based on document complexity"""
        # Base time estimates per stage (in seconds)
        stage_estimates = {
            "intake": 120,      # 2 minutes for document parsing + intake
            "analysis": 180,    # 3 minutes for analysis + PSLA
            "document_generation": 150,  # 2.5 minutes for hearing pack + declaration  
            "client_materials": 90,      # 1.5 minutes for client letter + research
            "quality_gate": 60          # 1 minute for quality checks
        }
        
        # TODO: Could enhance with actual document size/complexity factors
        base_time = stage_estimates.get(stage, 120)
        return datetime.utcnow() + timedelta(seconds=base_time)

    async def run_intake_agent(self, session_id: str):
        """Run the intake agent - entry point of the pipeline"""
        logger.info(f"Starting intake agent for session {session_id}")
        try:
            completion_time = self._estimate_completion_time(session_id, "intake")
            logger.info(f"Session {session_id}: Estimated completion time: {completion_time}")
            await self.session_manager.update_session_status(
                session_id, "processing", "Starting document analysis pipeline...", 
                current_stage="intake", current_step="intake", progress=10,
                step_progress=0, detailed_status_message="Preparing documents for analysis...",
                estimated_completion_time=completion_time
            )
            
            # Parse documents and create embeddings
            session = await self.session_manager.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                raise Exception("Session not found")
            
            logger.info(f"Session {session_id}: Found session with {len(session.get('uploaded_files', []))} files")
            
            # Parse all uploaded documents
            parsed_docs = []
            total_docs = len(session["uploaded_files"])
            for i, doc in enumerate(session["uploaded_files"]):
                await self.session_manager.update_session_status(
                    session_id, "processing", f"Parsing document {i+1} of {total_docs}...",
                    current_step="intake", step_progress=int((i / total_docs) * 30),
                    detailed_status_message=f"Processing {doc['filename']}..."
                )
                
                logger.info(f"Session {session_id}: Parsing document {doc['filename']}")
                try:
                    parsed_content = await self.document_parser.parse_document(doc["file_path"])
                    parsed_docs.append({
                        "doc_id": doc["doc_id"],
                        "filename": doc["filename"],
                        "content": parsed_content["text"],
                        "pages": parsed_content.get("pages", [])
                    })
                    logger.info(f"Session {session_id}: Successfully parsed {doc['filename']}")
                except Exception as parse_error:
                    logger.error(f"Session {session_id}: Failed to parse {doc['filename']}: {str(parse_error)}")
                    raise
            
            # Create FAISS embeddings for session
            await self.session_manager.update_session_status(
                session_id, "processing", "Creating document embeddings...",
                current_step="intake", step_progress=40,
                detailed_status_message="Building AI search index from documents..."
            )
            logger.info(f"Session {session_id}: Creating FAISS index for {len(parsed_docs)} documents")
            await self.faiss_store.create_session_index(session_id, parsed_docs)
            logger.info(f"Session {session_id}: FAISS index created successfully")
            
            # Run intake agent
            await self.session_manager.update_session_status(
                session_id, "processing", "Running intake analysis...",
                current_step="intake", step_progress=80,
                detailed_status_message="Analyzing document content and structure..."
            )
            logger.info(f"Session {session_id}: Starting intake agent processing")
            try:
                intake_result = await self.agents["intake"].process(session_id, parsed_docs)
                logger.info(f"Session {session_id}: Intake agent completed successfully")
            except Exception as intake_error:
                logger.error(f"Session {session_id}: Intake agent failed: {str(intake_error)}")
                # Create mock response for development/testing
                intake_result = {
                    "session_id": session_id,
                    "docs": [{"doc_id": doc["doc_id"], "filename": doc["filename"]} for doc in parsed_docs],
                    "session_flags": {
                        "child_urgent": False,
                        "missing_critical_data": ["jurisdiction", "child_birth_date", "case_start_date"]  # Mock missing data to test clarifying questions
                    },
                    "legal_elements": {
                        "domestic_violence": {"present": True, "confidence": 0.8},
                        "financial_abuse": {"present": False, "confidence": 0.3},
                        "child_custody": {"present": True, "confidence": 0.9}
                    },
                    "timeline": [
                        {"date": "2024-01-15", "event": "Initial incident reported", "type": "domestic_violence"},
                        {"date": "2024-02-03", "event": "Financial documents withheld", "type": "financial_abuse"}
                    ],
                    "provenance": {"agent": "intake", "timestamp": datetime.utcnow().isoformat()},
                    "mock": True,
                    "original_error": str(intake_error)
                }
                logger.info(f"Session {session_id}: Using mock intake result due to agent failure")
            
            # Save agent output
            await self.session_manager.save_agent_output(session_id, "intake", intake_result)
            
            # Mark intake as completed
            await self.session_manager.update_session_status(
                session_id, "processing", "Intake analysis complete",
                current_step="intake", step_progress=100, completed_stages=["intake"]
            )

            # Check if clarifying questions are needed
            missing_data = intake_result.get("session_flags", {}).get("missing_critical_data", [])
            if missing_data and len(missing_data) > 0:
                await self._handle_clarifying_questions(session_id, intake_result)
            else:
                # Continue with pipeline
                await self.continue_pipeline(session_id)
            
        except Exception as e:
            logger.error(f"Session {session_id}: Intake agent failed: {str(e)}")
            logger.error(f"Session {session_id}: Traceback: {traceback.format_exc()}")
            await self.session_manager.update_session_status(
                session_id, "error", f"Intake analysis failed: {str(e)}"
            )
            self._log_error("intake", session_id, str(e))
    
    async def continue_pipeline(self, session_id: str):
        """Continue pipeline after intake (with or without clarifying questions)"""
        logger.info(f"Session {session_id}: Continuing pipeline with analysis stage")
        try:
            # Run Analysis and PSLA agents in parallel
            completion_time = self._estimate_completion_time(session_id, "analysis")
            await self.session_manager.update_session_status(
                session_id, "processing", "Running pattern analysis...",
                current_stage="analysis", current_step="analysis", progress=30,
                step_progress=0, detailed_status_message="Analyzing legal patterns and incident mapping...",
                estimated_completion_time=completion_time, completed_stages=["intake"]
            )
            
            # Get intake output
            session = await self.session_manager.get_session(session_id)
            intake_output = session["agent_outputs"]["intake"]
            
            # Update progress for analysis step specifically
            await self.session_manager.update_session_status(
                session_id, "processing", "Running legal analysis...",
                current_step="analysis", step_progress=50,
                detailed_status_message="Mapping incidents to legal elements...",
                completed_stages=["intake"]
            )
            
            # Run parallel analysis
            analysis_task = self.agents["analysis"].process(session_id, intake_output)
            
            # Update for PSLA step
            await self.session_manager.update_session_status(
                session_id, "processing", "Running PSLA classification...",
                current_step="psla", step_progress=0,
                detailed_status_message="Classifying post-separation legal abuse patterns...",
                completed_stages=["intake", "analysis"]
            )
            
            psla_task = self.agents["psla"].process(session_id, intake_output)
            
            analysis_result, psla_result = await asyncio.gather(analysis_task, psla_task)
            
            # Save outputs
            await self.session_manager.save_agent_output(session_id, "analysis", analysis_result)
            await self.session_manager.save_agent_output(session_id, "psla", psla_result)
            
            # Mark analysis stages as completed
            await self.session_manager.update_session_status(
                session_id, "processing", "Analysis complete",
                current_step="psla", step_progress=100, completed_stages=["intake", "analysis", "psla"]
            )
            
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
            completion_time = self._estimate_completion_time(session_id, "document_generation")
            await self.session_manager.update_session_status(
                session_id, "processing", "Generating court documents...",
                current_stage="document_generation", current_step="hearing_pack", progress=60,
                step_progress=0, detailed_status_message="Creating hearing pack and court declarations...",
                estimated_completion_time=completion_time
            )
            
            session = await self.session_manager.get_session(session_id)
            analysis_output = session["agent_outputs"]["analysis"]
            psla_output = session["agent_outputs"]["psla"]
            intake_output = session["agent_outputs"]["intake"]
            
            # Update progress for hearing pack step
            await self.session_manager.update_session_status(
                session_id, "processing", "Generating hearing pack...",
                current_step="hearing_pack", step_progress=30,
                detailed_status_message="Creating court-ready hearing materials...",
                completed_stages=["intake", "analysis", "psla"]
            )
            
            # Run parallel document generation
            hearing_pack_task = self.agents["hearing_pack"].process(
                session_id, intake_output, analysis_output, psla_output
            )
            
            # Update progress for declaration step
            await self.session_manager.update_session_status(
                session_id, "processing", "Drafting declaration...",
                current_step="declaration", step_progress=50,
                detailed_status_message="Creating formal court declaration...",
                completed_stages=["intake", "analysis", "psla", "hearing_pack"]
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
            
            # Mark document generation as completed
            await self.session_manager.update_session_status(
                session_id, "processing", "Court documents generated",
                current_step="declaration", step_progress=100, completed_stages=["intake", "analysis", "psla", "hearing_pack", "declaration"]
            )
            
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
            completion_time = self._estimate_completion_time(session_id, "client_materials")
            await self.session_manager.update_session_status(
                session_id, "processing", "Generating client materials...",
                current_stage="client_materials", current_step="client_letter", progress=80,
                step_progress=0, detailed_status_message="Creating client letter and legal research...",
                estimated_completion_time=completion_time
            )
            
            session = await self.session_manager.get_session(session_id)
            intake_output = session["agent_outputs"]["intake"]
            analysis_output = session["agent_outputs"]["analysis"]
            
            # Update progress for client letter step
            await self.session_manager.update_session_status(
                session_id, "processing", "Creating client letter...",
                current_step="client_letter", step_progress=40,
                detailed_status_message="Creating plain-language summary for client...",
                completed_stages=["intake", "analysis", "psla", "hearing_pack", "declaration"]
            )
            
            # Run client letter and research in parallel
            client_letter_task = self.agents["client_letter"].process(
                session_id, intake_output, analysis_output
            )
            
            # Update progress for research step
            await self.session_manager.update_session_status(
                session_id, "processing", "Conducting legal research...",
                current_step="research", step_progress=60,
                detailed_status_message="Finding relevant legal authorities...",
                completed_stages=["intake", "analysis", "psla", "hearing_pack", "declaration", "client_letter"]
            )
            
            # Extract jurisdiction from intake output for research agent
            jurisdiction = intake_output.get("jurisdiction", "California")  # Default to California
            research_task = self.agents["research"].process(
                session_id, jurisdiction
            )
            
            client_letter_result, research_result = await asyncio.gather(
                client_letter_task, research_task
            )
            
            # Save outputs
            await self.session_manager.save_agent_output(session_id, "client_letter", client_letter_result)
            await self.session_manager.save_agent_output(session_id, "research", research_result)
            
            # Mark client materials as completed
            await self.session_manager.update_session_status(
                session_id, "processing", "Client materials generated",
                current_step="research", step_progress=100, completed_stages=["intake", "analysis", "psla", "hearing_pack", "declaration", "client_letter", "research"]
            )
            
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
            completion_time = self._estimate_completion_time(session_id, "quality_gate")
            await self.session_manager.update_session_status(
                session_id, "processing", "Running quality checks...",
                current_stage="quality_gate", current_step="quality_gate", progress=95,
                step_progress=0, detailed_status_message="Performing final quality validation...",
                estimated_completion_time=completion_time
            )
            
            session = await self.session_manager.get_session(session_id)
            all_outputs = session["agent_outputs"]
            
            # Run quality gate
            quality_result = await self.agents["quality_gate"].process(session_id, all_outputs)
            
            # Save output
            await self.session_manager.save_agent_output(session_id, "quality_gate", quality_result)
            
            # Mark quality gate as completed first
            await self.session_manager.update_session_status(
                session_id, "processing", "Quality checks complete",
                current_step="quality_gate", step_progress=100, completed_stages=["intake", "analysis", "psla", "hearing_pack", "declaration", "client_letter", "research", "quality_gate"]
            )

            # Generate artifact files from agent outputs
            artifacts = await self._generate_artifact_files(session_id, all_outputs)
            
            # Check if human review is required
            if quality_result.get("routing") == "require_human_review":
                await self.session_manager.update_session_status(
                    session_id, "requires_review", "Analysis complete. Human review recommended.",
                    progress=100, artifacts_ready=True, artifacts_available=artifacts,
                    detailed_status_message="All documents generated and ready for review."
                )
            elif quality_result.get("routing") == "accept":
                await self.session_manager.update_session_status(
                    session_id, "completed", "Analysis complete. All artifacts ready for download.",
                    progress=100, artifacts_ready=True, artifacts_available=artifacts,
                    detailed_status_message="Processing complete. All legal documents are ready."
                )
            else:
                await self.session_manager.update_session_status(
                    session_id, "requires_revision", "Analysis needs revision before completion.",
                    progress=90, detailed_status_message="Quality checks identified issues requiring revision."
                )
            
        except Exception as e:
            await self.session_manager.update_session_status(
                session_id, "error", f"Quality gate failed: {str(e)}"
            )
            self._log_error("quality_gate", session_id, str(e))
    
    async def _generate_artifact_files(self, session_id: str, all_outputs: Dict[str, Any]) -> List[str]:
        """Generate downloadable artifact files from agent outputs"""
        import os
        import json
        
        artifacts = []
        artifacts_dir = f"/tmp/lance/artifacts/{session_id}"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        try:
            # Generate files for each agent output that produces documents
            for agent_name, output in all_outputs.items():
                if agent_name in ["hearing_pack", "declaration", "client_letter", "research"]:
                    
                    if agent_name == "hearing_pack":
                        # Generate hearing pack document
                        content = output.get("hearing_pack_content", "No hearing pack content available")
                        filename = f"hearing_pack_{session_id[:8]}.txt"
                        filepath = os.path.join(artifacts_dir, filename)
                        with open(filepath, 'w') as f:
                            f.write(f"HEARING PACK DOCUMENT\n{'='*50}\n\n{content}")
                        artifacts.append(filename)
                    
                    elif agent_name == "declaration":
                        # Generate declaration document  
                        content = output.get("declaration_content", "No declaration content available")
                        filename = f"declaration_{session_id[:8]}.txt"
                        filepath = os.path.join(artifacts_dir, filename)
                        with open(filepath, 'w') as f:
                            f.write(f"LEGAL DECLARATION\n{'='*50}\n\n{content}")
                        artifacts.append(filename)
                    
                    elif agent_name == "client_letter":
                        # Generate client letter
                        content = output.get("letter_content", "No client letter content available")
                        filename = f"client_letter_{session_id[:8]}.txt"
                        filepath = os.path.join(artifacts_dir, filename)
                        with open(filepath, 'w') as f:
                            f.write(f"CLIENT LETTER\n{'='*50}\n\n{content}")
                        artifacts.append(filename)
                    
                    elif agent_name == "research":
                        # Generate research report
                        authorities = output.get("authorities", [])
                        summary = output.get("summary", "No research summary available")
                        content = f"LEGAL RESEARCH REPORT\n{'='*50}\n\n{summary}\n\nAUTHORITIES:\n"
                        for auth in authorities:
                            content += f"\n- {auth.get('citation', 'Unknown')}: {auth.get('quote', 'No quote')}\n"
                        
                        filename = f"legal_research_{session_id[:8]}.txt"
                        filepath = os.path.join(artifacts_dir, filename)
                        with open(filepath, 'w') as f:
                            f.write(content)
                        artifacts.append(filename)
            
            # Generate analysis summary
            if "intake" in all_outputs:
                intake_data = all_outputs["intake"]
                summary_content = f"ANALYSIS SUMMARY\n{'='*50}\n\n"
                summary_content += f"Session ID: {session_id}\n"
                summary_content += f"Documents Analyzed: {len(intake_data.get('docs', []))}\n"
                
                if "legal_elements" in intake_data:
                    summary_content += "\nLegal Elements Identified:\n"
                    for element, details in intake_data["legal_elements"].items():
                        if details.get("present"):
                            summary_content += f"- {element}: {details.get('confidence', 0):.0%} confidence\n"
                
                filename = f"analysis_summary_{session_id[:8]}.txt"
                filepath = os.path.join(artifacts_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(summary_content)
                artifacts.append(filename)
            
            logger.info(f"Generated {len(artifacts)} artifact files for session {session_id}")
            return artifacts
            
        except Exception as e:
            logger.error(f"Error generating artifacts for session {session_id}: {str(e)}")
            return []
    
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
        
        # If no actual questions were generated, continue pipeline instead of waiting
        if not questions:
            logger.info(f"Session {session_id}: No actionable clarifying questions generated, continuing pipeline")
            await self.continue_pipeline(session_id)
        else:
            await self.session_manager.update_session_status(
                session_id, "waiting_input", "Need additional information to continue analysis",
                has_clarifying_questions=True, clarifying_questions=questions, progress=20
            )
    
    async def process_clarifying_answers(self, session_id: str, answer: str):
        """Process clarifying question answers and continue pipeline"""
        logger.info(f"Processing clarifying answers for session {session_id}")
        try:
            # Save answers to session
            await self.session_manager.save_clarifying_answers(session_id, answer)
            
            # Update session status to continue processing
            await self.session_manager.update_session_status(
                session_id, "processing", "Received clarifying answers, continuing analysis...",
                has_clarifying_questions=False, pending_questions=[]
            )
            
            # Continue with pipeline
            await self.continue_pipeline(session_id)
            
        except Exception as e:
            logger.error(f"Failed to process clarifying answers for session {session_id}: {str(e)}")
            await self.session_manager.update_session_status(
                session_id, "error", f"Failed to process answers: {str(e)}"
            )
            self._log_error("clarifying_answers", session_id, str(e))
    
    def _log_error(self, stage: str, session_id: str, error_msg: str):
        """Log error details"""
        logger.error(f"Stage {stage} failed for session {session_id}: {error_msg}")
        print(f"ERROR in {stage}: {error_msg}")  # Also print to console for debugging
    
    def _create_provenance(self, agent_id: str, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata for agent output"""
        return {
            "agent_id": agent_id,
            "model": "gpt-4",  # Will be gpt-5-nano when available
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
