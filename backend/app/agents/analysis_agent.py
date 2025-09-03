import json
import uuid
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.faiss_store import FAISSStore

class AnalysisAgent:
    """Coercive-Control Pattern Analysis Agent"""
    
    def __init__(self, llm: ChatOpenAI, faiss_store: FAISSStore):
        self.llm = llm
        self.faiss_store = faiss_store
        self.agent_id = "analysis"
    
    async def process(self, session_id: str, intake_output: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze incidents for coercive control patterns"""
        try:
            # Search for coercive control patterns in documents
            pattern_evidence = await self._search_coercive_patterns(session_id)
            
            # Create prompt with intake data and pattern evidence
            prompt = self._create_analysis_prompt(intake_output, pattern_evidence)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_empty_response(session_id, "JSON parsing error")
            
            # Enhance with FAISS retrieval for supporting evidence
            result = await self._enhance_with_retrieval(session_id, result)
            
            # Validate output
            result = self._validate_analysis_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_empty_response(session_id, f"Analysis error: {str(e)}")
    
    async def _search_coercive_patterns(self, session_id: str) -> List[Dict[str, Any]]:
        """Search for coercive control patterns using vector database"""
        pattern_queries = [
            "isolation from family friends support network",
            "monitoring surveillance tracking location",
            "financial control restricting access money",
            "threats intimidation fear safety",
            "gaslighting manipulation reality questioning",
            "using children leverage manipulation custody",
            "legal abuse frivolous lawsuits motions"
        ]
        
        all_results = []
        for query in pattern_queries:
            results = await self.faiss_store.search_session(session_id, query, k=5)
            all_results.extend(results)
        
        return all_results[:20]  # Return top 20 most relevant chunks
    
    def _create_analysis_prompt(self, intake_output: Dict[str, Any], pattern_evidence: List[Dict[str, Any]]) -> str:
        """Create analysis prompt with pattern evidence"""
        incidents = []
        for doc in intake_output.get("docs", []):
            for incident in doc.get("incidents", []):
                incidents.append({
                    **incident,
                    "source_doc": doc.get("doc_id", "unknown")
                })
        
        # Format pattern evidence
        evidence_text = "\n\nCOERCIVE CONTROL EVIDENCE FROM DOCUMENTS:\n"
        for i, evidence in enumerate(pattern_evidence[:10], 1):
            evidence_text += f"\n{i}. [Doc: {evidence['doc_id']}]\n"
            evidence_text += f"   Text: {evidence['text'][:150]}...\n"
        
        # Summarize incidents
        incident_summaries = []
        for i, incident in enumerate(incidents[:10]):  # Limit to first 10 to avoid token limits
            incident_summaries.append(f"""
Incident {i+1}:
- ID: {incident.get('incident_id', f'inc_{i+1}')}
- Type: {incident.get('wheel_tag', 'Unknown')}
- Summary: {incident.get('summary', 'No summary')}
- Quote: "{incident.get('quote_span', 'No quote')}"
- Actor: {incident.get('actor', 'Unknown')}
- Target: {incident.get('target', 'Unknown')}
- Confidence: {incident.get('confidence', 0)}
""")
        
        return f"""Act as a forensic pattern-analyst specializing in coercive control. Map incidents to legal elements and assess severity.\n\nINCIDENTS TO ANALYZE:\n{json.dumps(incidents, indent=2)}\n{evidence_text}\n\nMap each incident to legal elements with severity scores (0-1). Look for patterns of: 

Legal elements to consider:
1. Pattern of Control and Dominance
2. Isolation and Social Control
3. Economic Control and Abuse
4. Threats and Intimidation
5. Use of Children as Weapons
6. Legal System Abuse
7. Psychological and Emotional Abuse
8. Surveillance and Monitoring

For each incident, map to relevant legal elements and provide:
- Element name
- Statutory standard (if known for jurisdiction)
- Fact support (with exact quote, doc_id, page, line_range)
- Counter evidence (if any)
- Severity score (0-5)
- Confidence score (0-1)

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "mappings": [
        {{
            "incident_id": "inc_1",
            "wheel_tag": "CoerciveControl",
            "summary": "Brief incident summary",
            "legal_elements": [
                {{
                    "element": "Pattern of Control and Dominance",
                    "statutory_standard": "Relevant law if known",
                    "fact_support": [
                        {{
                            "quote": "Exact quote from document",
                            "doc_id": "doc_1",
                            "page": 1,
                            "line_range": "5-7"
                        }}
                    ],
                    "counter_evidence": [],
                    "severity": 3,
                    "confidence": 0.8
                }}
            ]
        }}
    ],
    "recommendations": [
        {{
            "recommendation": "Specific recommendation",
            "reason": "Legal reasoning"
        }}
    ],
    "provenance": {{}}
}}

CRITICAL: Every fact_support entry must include exact quote, doc_id, page, and line_range. If missing, set confidence to 0."""
    
    async def _enhance_with_retrieval(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance analysis with additional supporting evidence from FAISS"""
        try:
            for mapping in result.get("mappings", []):
                for element in mapping.get("legal_elements", []):
                    element_name = element.get("element", "")
                    
                    # Search for additional supporting evidence
                    additional_quotes = await self.faiss_store.get_supporting_quotes(
                        session_id, 
                        f"{element_name} {mapping.get('wheel_tag', '')}", 
                        min_score=0.7
                    )
                    
                    # Add top 2 additional quotes if they're not already included
                    existing_quotes = {fs["quote"] for fs in element.get("fact_support", [])}
                    
                    for quote in additional_quotes[:2]:
                        if quote["text"] not in existing_quotes:
                            element["fact_support"].append({
                                "quote": quote["text"][:200],  # Truncate long quotes
                                "doc_id": quote["doc_id"],
                                "page": quote["page"],
                                "line_range": quote["line_range"]
                            })
            
            return result
            
        except Exception as e:
            # Don't fail the entire analysis if retrieval fails
            result["retrieval_error"] = str(e)
            return result
    
    def _validate_analysis_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean analysis output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            if "mappings" not in result:
                result["mappings"] = []
            
            if "recommendations" not in result:
                result["recommendations"] = []
            
            # Validate mappings
            validated_mappings = []
            for mapping in result.get("mappings", []):
                validated_elements = []
                
                for element in mapping.get("legal_elements", []):
                    # Check if element has proper fact support
                    if element.get("fact_support") and len(element["fact_support"]) > 0:
                        # Check if all fact support has required fields
                        valid_support = []
                        for support in element["fact_support"]:
                            if all(field in support for field in ["quote", "doc_id", "page", "line_range"]):
                                valid_support.append(support)
                        
                        if valid_support:
                            element["fact_support"] = valid_support
                            validated_elements.append(element)
                        else:
                            # No valid support - reduce confidence
                            element["confidence"] = 0.0
                            element["validation_note"] = "No valid fact support"
                            validated_elements.append(element)
                
                if validated_elements:
                    mapping["legal_elements"] = validated_elements
                    validated_mappings.append(mapping)
            
            result["mappings"] = validated_mappings
            
            # Add provenance
            result["provenance"] = self._create_provenance("")
            
            return result
            
        except Exception as e:
            result["validation_error"] = str(e)
            return result
    
    def _create_empty_response(self, session_id: str, error_msg: str) -> Dict[str, Any]:
        """Create empty response for error cases"""
        return {
            "session_id": session_id,
            "mappings": [],
            "recommendations": [],
            "error": error_msg,
            "provenance": self._create_provenance("")
        }
    
    def _create_provenance(self, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata"""
        return {
            "agent_id": self.agent_id,
            "model": "gpt-4",
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
