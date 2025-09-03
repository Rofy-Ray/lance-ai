import json
import uuid
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.faiss_store import FAISSStore

class IntakeAgent:
    """Document Intake & Safety Triage Agent"""
    
    def __init__(self, llm: ChatOpenAI, faiss_store: FAISSStore):
        self.llm = llm
        self.faiss_store = faiss_store
        self.agent_id = "intake"
        
        # Load abuse wheel data
        self.wheel_data = self._load_wheel_data()
        
    def _load_wheel_data(self) -> Dict[str, List[str]]:
        """Load post-separation abuse wheel data"""
        wheel_path = Path(__file__).parent.parent.parent.parent / "agents" / "data" / "wheel.json"
        with open(wheel_path, 'r') as f:
            return json.load(f)
    
    async def process(self, session_id: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process documents for intake analysis"""
        try:
            # First, search for key patterns using vector database
            key_patterns = await self._search_key_patterns(session_id)
            
            # Create prompt with wheel data, document content, and search results
            prompt = self._create_intake_prompt(session_id, documents, key_patterns)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a basic response
                result = {
                    "session_id": session_id,
                    "docs": [],
                    "session_flags": {
                        "child_urgent": False,
                        "missing_critical_data": ["json_parse_error"]
                    },
                    "provenance": self._create_provenance(prompt)
                }
            
            # Validate and enhance result
            result = await self._validate_intake_output(session_id, result, documents)
            
            return result
            
        except Exception as e:
            return {
                "session_id": session_id,
                "docs": [],
                "session_flags": {
                    "child_urgent": False,
                    "missing_critical_data": [f"processing_error: {str(e)}"]
                },
                "provenance": self._create_provenance(""),
                "error": str(e)
            }
    
    async def _search_key_patterns(self, session_id: str) -> List[Dict[str, Any]]:
        """Search for key patterns in documents using vector database"""
        key_searches = [
            "domestic violence abuse coercive control",
            "financial abuse economic control money",
            "child custody parenting time visitation",
            "restraining order protection order TRO",
            "harassment stalking threats intimidation",
            "legal proceedings court filings motions",
            "post-separation abuse divorce proceedings"
        ]
        
        all_results = []
        for query in key_searches:
            results = await self.faiss_store.search_session(session_id, query, k=3)
            all_results.extend(results)
        
        # Deduplicate and sort by relevance
        seen = set()
        unique_results = []
        for result in sorted(all_results, key=lambda x: x.get('score', float('inf'))):
            key = (result['doc_id'], result['text'][:50])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
                if len(unique_results) >= 15:
                    break
        
        return unique_results
    
    def _create_intake_prompt(self, session_id: str, documents: List[Dict[str, Any]], search_results: List[Dict[str, Any]]) -> str:
        """Create intake analysis prompt with vector search results"""
        # Summarize documents for context
        doc_summaries = []
        for doc in documents:
            content_preview = doc["content"][:1000] + "..." if len(doc["content"]) > 1000 else doc["content"]
            doc_summaries.append(f"Document ID: {doc['doc_id']}\nFilename: {doc['filename']}\nContent Preview:\n{content_preview}\n")
        
        # Format search results
        search_evidence = "\n\nKEY EVIDENCE FROM VECTOR SEARCH:\n"
        for i, result in enumerate(search_results[:10], 1):
            search_evidence += f"\n{i}. [Doc: {result['doc_id']}, Page: {result.get('page', 'N/A')}]\n"
            search_evidence += f"   Text: {result['text'][:200]}...\n"
        
        # Create wheel categories description
        wheel_descriptions = []
        for category, patterns in self.wheel_data.items():
            wheel_descriptions.append(f"{category}: {', '.join(patterns[:2])}...")
        
        return f"""Act as a trauma-informed family-law triage analyst. From the attached documents for session {session_id}, extract incidents and tag them using the post-separation abuse wheel. Return only a JSON matching the intake schema. For any missing critical data ask up to 3 clarifying questions. Do not guess.

Post-Separation Abuse Wheel Categories:
{chr(10).join(wheel_descriptions)}

Documents to analyze:
{chr(10).join(doc_summaries)}
{search_evidence}

CRITICAL REQUIREMENTS:
1. Every incident MUST include: quote_span, doc_id, page, line_range
2. If missing critical data (jurisdiction, child DOB, etc.), add to missing_critical_data array
3. Set urgent_flag=true only if confidence >= 0.6 AND you have a direct quote
4. Do not invent or guess information

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "docs": [
        {{
            "doc_id": "doc_1",
            "type": "court_filing",
            "date": "2023-01-01",
            "parties": ["Party A", "Party B"],
            "summary": "Brief document summary",
            "wheel_tags": ["CoerciveControl", "LegalAbuse"],
            "incidents": [
                {{
                    "incident_id": "inc_1",
                    "date": "2023-01-01",
                    "actor": "Party A",
                    "target": "Party B", 
                    "wheel_tag": "CoerciveControl",
                    "summary": "Brief incident description",
                    "quote_span": "Exact quote from document",
                    "page": 1,
                    "line_range": "5-7",
                    "confidence": 0.8,
                    "urgent_flag": false
                }}
            ]
        }}
    ],
    "session_flags": {{
        "child_urgent": false,
        "missing_critical_data": ["jurisdiction", "child_birth_dates"]
    }},
    "provenance": {{}}
}}"""
    
    async def _validate_intake_output(self, session_id: str, result: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and enhance intake output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            if "docs" not in result:
                result["docs"] = []
            
            if "session_flags" not in result:
                result["session_flags"] = {"child_urgent": False, "missing_critical_data": []}
            
            # Validate incidents have required quote information
            validated_docs = []
            for doc in result.get("docs", []):
                validated_incidents = []
                
                for incident in doc.get("incidents", []):
                    # Check if incident has required fields
                    if all(field in incident for field in ["quote_span", "page", "line_range"]):
                        # Verify quote exists in document content
                        if await self._verify_quote_exists(incident, documents):
                            validated_incidents.append(incident)
                        else:
                            # Quote not found, mark as insufficient evidence
                            incident["confidence"] = 0.0
                            incident["urgent_flag"] = False
                            incident["validation_note"] = "Quote not verified in document"
                            validated_incidents.append(incident)
                    else:
                        # Missing required fields - add to missing data
                        if "missing_quote_data" not in result["session_flags"]["missing_critical_data"]:
                            result["session_flags"]["missing_critical_data"].append("missing_quote_data")
                
                doc["incidents"] = validated_incidents
                validated_docs.append(doc)
            
            result["docs"] = validated_docs
            
            # Add provenance
            result["provenance"] = self._create_provenance("")
            
            return result
            
        except Exception as e:
            result["validation_error"] = str(e)
            return result
    
    async def _verify_quote_exists(self, incident: Dict[str, Any], documents: List[Dict[str, Any]]) -> bool:
        """Verify quote exists in the referenced document"""
        try:
            quote_span = incident.get("quote_span", "")
            doc_id = incident.get("doc_id", "")
            
            # Find the document
            target_doc = None
            for doc in documents:
                if doc["doc_id"] == doc_id:
                    target_doc = doc
                    break
            
            if not target_doc:
                return False
            
            # Simple text search (case-insensitive)
            return quote_span.lower() in target_doc["content"].lower()
            
        except Exception:
            return False
    
    def _create_provenance(self, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata"""
        return {
            "agent_id": self.agent_id,
            "model": "gpt-4",
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
