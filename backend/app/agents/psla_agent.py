import json
from typing import Dict, Any, List
from datetime import datetime

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.faiss_store import FAISSStore

class PSLAAgent:
    """Post-Separation Legal Abuse (PSLA) Detector Agent"""
    
    def __init__(self, llm: ChatOpenAI, faiss_store: FAISSStore):
        self.llm = llm
        self.faiss_store = faiss_store
        self.agent_id = "psla"
    
    async def process(self, session_id: str, intake_output: Dict[str, Any]) -> Dict[str, Any]:
        """Classify filings and detect legal abuse patterns"""
        try:
            # Extract filings from intake
            filings = self._extract_filings(intake_output)
            
            if not filings:
                return self._create_empty_response(session_id, "No filings found for PSLA analysis")
            
            # Create PSLA analysis prompt
            prompt = self._create_psla_prompt(session_id, filings)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_empty_response(session_id, "JSON parsing error")
            
            # Calculate additional metrics
            result = self._calculate_metrics(result, filings)
            
            # Validate output
            result = self._validate_psla_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_empty_response(session_id, f"PSLA analysis error: {str(e)}")
    
    def _extract_filings(self, intake_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract legal filings from intake output"""
        filings = []
        
        for doc in intake_output.get("docs", []):
            # Identify legal filings vs other documents
            doc_type = doc.get("type", "").lower()
            filename = doc.get("filename", "").lower()
            
            is_filing = any(term in doc_type or term in filename for term in [
                "motion", "petition", "brief", "pleading", "filing", "complaint", 
                "response", "reply", "order", "judgment", "subpoena", "discovery"
            ])
            
            if is_filing or doc.get("incidents"):  # Include docs with incidents
                filing_info = {
                    "filing_id": f"filing_{len(filings) + 1}",
                    "doc_id": doc.get("doc_id", "unknown"),
                    "filename": doc.get("filename", "unknown"),
                    "type": doc.get("type", "unknown"),
                    "date": doc.get("date"),
                    "summary": doc.get("summary", ""),
                    "incidents": doc.get("incidents", []),
                    "parties": doc.get("parties", [])
                }
                filings.append(filing_info)
        
        return filings
    
    def _create_psla_prompt(self, session_id: str, filings: List[Dict[str, Any]]) -> str:
        """Create PSLA analysis prompt"""
        
        filing_summaries = []
        for i, filing in enumerate(filings[:8]):  # Limit to avoid token limits
            incident_count = len(filing.get("incidents", []))
            filing_summaries.append(f"""
Filing {i+1}:
- ID: {filing.get('filing_id')}
- Document: {filing.get('filename')}
- Type: {filing.get('type')}
- Date: {filing.get('date', 'Unknown')}
- Incidents: {incident_count}
- Summary: {filing.get('summary', 'No summary')[:200]}
""")
        
        return f"""Act as a litigation-risk analyst. Classify each filing as routine|aggressive|abusive with two supporting citations. Compute filing_repetition_index and novelty_score.

Session ID: {session_id}

Filings to analyze:
{chr(10).join(filing_summaries)}

Classification Guidelines:
- ROUTINE: Standard legal procedure, appropriate timing, reasonable requests
- AGGRESSIVE: Excessive demands, inappropriate timing, but within legal bounds
- ABUSIVE: Frivolous motions, harassment, bad faith, pattern of abuse

For each filing, provide:
1. Classification (routine/aggressive/abusive)
2. Rationale explaining the classification
3. At least 2 supporting quote spans with exact citations
4. Filing repetition index (0-1): How repetitive/frivolous compared to others
5. Novelty score (0-1): How novel/unusual the legal arguments are
6. False positive risk (low/medium/high)

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "findings": [
        {{
            "filing_id": "filing_1",
            "doc_id": "doc_1", 
            "date": "2023-01-01",
            "classification": "abusive",
            "rationale": "Detailed explanation of classification",
            "quote_spans": [
                {{
                    "quote": "Exact quote supporting classification",
                    "doc_id": "doc_1",
                    "page": 1,
                    "line_range": "5-7"
                }},
                {{
                    "quote": "Second supporting quote",
                    "doc_id": "doc_1", 
                    "page": 2,
                    "line_range": "10-12"
                }}
            ],
            "filing_repetition_index": 0.8,
            "novelty_score": 0.2,
            "false_positive_risk": "low"
        }}
    ],
    "summary": "Overall PSLA pattern summary",
    "provenance": {{}}
}}

CRITICAL: 
- Each 'abusive' classification MUST have at least 2 supporting quotes
- Quote spans must include exact quote, doc_id, page, line_range
- Be conservative with 'abusive' classifications - require clear evidence"""
    
    def _calculate_metrics(self, result: Dict[str, Any], filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate additional PSLA metrics"""
        try:
            findings = result.get("findings", [])
            
            if not findings:
                return result
            
            # Calculate overall pattern metrics
            classifications = [f.get("classification", "routine") for f in findings]
            abusive_count = classifications.count("abusive")
            aggressive_count = classifications.count("aggressive")
            total_count = len(classifications)
            
            # Add summary metrics
            pattern_summary = {
                "total_filings": total_count,
                "abusive_filings": abusive_count,
                "aggressive_filings": aggressive_count,
                "routine_filings": total_count - abusive_count - aggressive_count,
                "abuse_percentage": (abusive_count / total_count * 100) if total_count > 0 else 0,
                "pattern_severity": "high" if abusive_count >= 3 else "medium" if abusive_count >= 1 else "low"
            }
            
            # Update summary
            existing_summary = result.get("summary", "")
            enhanced_summary = f"{existing_summary}\n\nPattern Analysis: {pattern_summary['abuse_percentage']:.1f}% abusive filings detected ({abusive_count}/{total_count}). Pattern severity: {pattern_summary['pattern_severity']}."
            
            result["summary"] = enhanced_summary.strip()
            result["pattern_metrics"] = pattern_summary
            
            return result
            
        except Exception as e:
            result["metrics_error"] = str(e)
            return result
    
    def _validate_psla_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean PSLA output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            if "findings" not in result:
                result["findings"] = []
            
            if "summary" not in result:
                result["summary"] = "No PSLA patterns detected"
            
            # Validate findings
            validated_findings = []
            for finding in result.get("findings", []):
                classification = finding.get("classification", "routine")
                quote_spans = finding.get("quote_spans", [])
                
                # Validate abusive classifications have sufficient quotes
                if classification == "abusive":
                    valid_quotes = [q for q in quote_spans if all(field in q for field in ["quote", "doc_id", "page", "line_range"])]
                    
                    if len(valid_quotes) < 2:
                        # Insufficient evidence for abusive classification
                        finding["classification"] = "aggressive"
                        finding["rationale"] = f"Downgraded from abusive due to insufficient evidence. {finding.get('rationale', '')}"
                        finding["validation_note"] = "Classification downgraded - insufficient quote evidence"
                
                # Ensure required numeric fields
                finding["filing_repetition_index"] = float(finding.get("filing_repetition_index", 0.0))
                finding["novelty_score"] = float(finding.get("novelty_score", 0.5))
                
                if "false_positive_risk" not in finding:
                    finding["false_positive_risk"] = "medium"
                
                validated_findings.append(finding)
            
            result["findings"] = validated_findings
            
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
            "findings": [],
            "summary": "PSLA analysis could not be completed",
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
