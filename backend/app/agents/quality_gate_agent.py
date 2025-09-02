import json
from typing import Dict, Any, List
from datetime import datetime
import re

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

class QualityGateAgent:
    """Quality / Bias / Hallucination Gate Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agent_id = "quality_gate"
    
    async def process(self, session_id: str, all_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Score artifacts for quality, bias, and hallucination risk"""
        try:
            # Create quality evaluation prompt
            prompt = self._create_quality_prompt(session_id, all_outputs)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_default_evaluation(session_id, "JSON parsing error")
            
            # Perform additional validation checks
            result = await self._perform_validation_checks(session_id, result, all_outputs)
            
            # Determine routing based on scores
            result = self._determine_routing(result)
            
            # Validate output
            result = self._validate_quality_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_default_evaluation(session_id, f"Quality gate error: {str(e)}")
    
    def _create_quality_prompt(self, session_id: str, all_outputs: Dict[str, Dict[str, Any]]) -> str:
        """Create quality evaluation prompt"""
        
        # Extract key statistics from outputs
        artifacts_summary = {}
        
        # Count citations across all outputs
        total_citations = 0
        total_findings = 0
        
        # Intake statistics
        if "intake" in all_outputs:
            intake = all_outputs["intake"]
            incident_count = sum(len(doc.get("incidents", [])) for doc in intake.get("docs", []))
            urgent_incidents = sum(1 for doc in intake.get("docs", []) for inc in doc.get("incidents", []) if inc.get("urgent_flag"))
            artifacts_summary["intake"] = {
                "incidents": incident_count,
                "urgent_flags": urgent_incidents,
                "child_urgent": intake.get("session_flags", {}).get("child_urgent", False)
            }
            total_findings += incident_count
        
        # Analysis statistics
        if "analysis" in all_outputs:
            analysis = all_outputs["analysis"]
            mappings_count = len(analysis.get("mappings", []))
            high_severity = sum(1 for m in analysis.get("mappings", []) for e in m.get("legal_elements", []) if e.get("severity", 0) >= 4)
            artifacts_summary["analysis"] = {
                "mappings": mappings_count,
                "high_severity_elements": high_severity
            }
            
            # Count citations
            for mapping in analysis.get("mappings", []):
                for element in mapping.get("legal_elements", []):
                    total_citations += len(element.get("fact_support", []))
        
        # PSLA statistics
        if "psla" in all_outputs:
            psla = all_outputs["psla"]
            findings_count = len(psla.get("findings", []))
            abusive_count = sum(1 for f in psla.get("findings", []) if f.get("classification") == "abusive")
            artifacts_summary["psla"] = {
                "total_findings": findings_count,
                "abusive_classifications": abusive_count
            }
        
        # Hearing pack statistics  
        if "hearing_pack" in all_outputs:
            hp = all_outputs["hearing_pack"]
            findings_count = len(hp.get("proposed_findings", []))
            citations_per_finding = findings_count and sum(len(f.get("quote_spans", [])) for f in hp.get("proposed_findings", [])) / findings_count
            artifacts_summary["hearing_pack"] = {
                "proposed_findings": findings_count,
                "avg_citations_per_finding": round(citations_per_finding, 2) if findings_count else 0
            }
        
        return f"""Score artifacts for citation density, quote fidelity, jurisdiction fit, trauma tone, child safety, and hallucination risk. Return eval.json.

Session ID: {session_id}

Artifacts Summary:
{json.dumps(artifacts_summary, indent=2)}

Citation Statistics:
- Total Citations: {total_citations}
- Total Findings: {total_findings} 
- Citation Density: {round(total_citations/max(total_findings, 1), 2)} citations per finding

Evaluate each dimension on a 0-5 scale:

1. CITATION_DENSITY (0-5): How well are claims supported by evidence?
   - 0: No citations
   - 3: Adequate citations (1+ per finding)
   - 5: Excellent citations (2+ per finding)

2. QUOTE_FIDELITY (0-5): How accurate are the quotes vs source docs?
   - 0: Fabricated quotes
   - 3: Mostly accurate quotes
   - 5: Perfect quote accuracy

3. JURISDICTION_FIT (0-5): How relevant are legal references to jurisdiction?
   - 0: Wrong jurisdiction
   - 3: Generic/federal law
   - 5: Jurisdiction-specific law

4. TRAUMA_TONE (0-5): How trauma-informed is the language?
   - 0: Victim-blaming language
   - 3: Neutral language
   - 5: Trauma-informed, survivor-centered

5. CHILD_SAFETY_CALIBRATION (0-5): How appropriately are child safety issues flagged?
   - 0: Missed serious child safety issues
   - 3: Appropriate child safety analysis
   - 5: Excellent child safety prioritization

6. HALLUCINATION_RISK (0-5): Risk of fabricated facts or legal authority?
   - 0: No hallucination risk - all claims cited
   - 1-2: Low risk - minor unsupported claims
   - 3-4: Medium risk - some uncited assertions
   - 5: High risk - significant fabricated content

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "scores": {{
        "citation_density": 3.5,
        "quote_fidelity": 4.0,
        "jurisdiction_fit": 3.0,
        "trauma_tone": 4.5,
        "child_safety_calibration": 4.0,
        "hallucination_risk": 1.0
    }},
    "remediation": [
        "Specific recommendation for improvement 1",
        "Specific recommendation for improvement 2",
        "Specific recommendation for improvement 3"
    ],
    "routing": "accept",
    "notes": "Overall assessment and key observations",
    "provenance": {{}}
}}

CRITICAL ROUTING RULES:
- hallucination_risk > 0: Route to "require_human_review"
- child_urgent flagged but citation_density < 2.0: Route to "require_human_review" 
- Overall scores average < 3.0: Route to "return_to_retrieval"
- Otherwise: Route to "accept"

Provide specific, actionable remediation steps."""
    
    async def _perform_validation_checks(self, session_id: str, result: Dict[str, Any], all_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Perform additional validation checks beyond LLM scoring"""
        
        validation_issues = []
        
        # Check for child urgent flag consistency
        intake = all_outputs.get("intake", {})
        child_urgent = intake.get("session_flags", {}).get("child_urgent", False)
        
        if child_urgent:
            # Verify urgent incidents have proper citations
            urgent_incidents = []
            for doc in intake.get("docs", []):
                for incident in doc.get("incidents", []):
                    if incident.get("urgent_flag"):
                        urgent_incidents.append(incident)
            
            uncited_urgent = [inc for inc in urgent_incidents if not inc.get("quote_span") or len(inc.get("quote_span", "")) < 10]
            
            if uncited_urgent:
                validation_issues.append(f"Child urgent flagged but {len(uncited_urgent)} urgent incidents lack proper citations")
                # Increase hallucination risk
                current_risk = result.get("scores", {}).get("hallucination_risk", 0)
                result["scores"]["hallucination_risk"] = min(5, current_risk + 2)
        
        # Check for quote consistency
        quote_validation_issues = await self._validate_quote_consistency(all_outputs)
        validation_issues.extend(quote_validation_issues)
        
        # Check for legal authority fabrication
        authority_issues = self._validate_legal_authorities(all_outputs)
        validation_issues.extend(authority_issues)
        
        if validation_issues:
            result["validation_issues"] = validation_issues
            existing_remediation = result.get("remediation", [])
            existing_remediation.extend([f"Validation: {issue}" for issue in validation_issues[:3]])
            result["remediation"] = existing_remediation
        
        return result
    
    async def _validate_quote_consistency(self, all_outputs: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check for quote consistency across outputs"""
        issues = []
        
        # Extract all quoted spans
        all_quotes = {}  # quote_text -> [locations]
        
        # From intake
        for doc in all_outputs.get("intake", {}).get("docs", []):
            for incident in doc.get("incidents", []):
                quote = incident.get("quote_span", "").strip()
                if len(quote) > 10:
                    if quote not in all_quotes:
                        all_quotes[quote] = []
                    all_quotes[quote].append(f"intake:{incident.get('incident_id')}")
        
        # From analysis
        for mapping in all_outputs.get("analysis", {}).get("mappings", []):
            for element in mapping.get("legal_elements", []):
                for support in element.get("fact_support", []):
                    quote = support.get("quote", "").strip()
                    if len(quote) > 10:
                        if quote not in all_quotes:
                            all_quotes[quote] = []
                        all_quotes[quote].append(f"analysis:{element.get('element')}")
        
        # Look for suspicious patterns
        very_long_quotes = [q for q in all_quotes.keys() if len(q) > 500]
        if very_long_quotes:
            issues.append(f"Found {len(very_long_quotes)} suspiciously long quotes (>500 chars)")
        
        # Look for repeated identical quotes
        repeated_quotes = [q for q, locs in all_quotes.items() if len(locs) > 3]
        if repeated_quotes:
            issues.append(f"Found {len(repeated_quotes)} quotes repeated >3 times across outputs")
        
        return issues
    
    def _validate_legal_authorities(self, all_outputs: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check for fabricated legal authorities"""
        issues = []
        
        research_output = all_outputs.get("research", {})
        authorities = research_output.get("authorities", [])
        
        # Check for suspicious case citations
        case_citations = [auth["citation"] for auth in authorities if auth.get("type") == "case"]
        
        for citation in case_citations:
            # Basic format validation for case citations
            has_v_pattern = " v. " in citation or " v " in citation
            has_year = re.search(r"\(\d{4}\)", citation)
            
            if not has_v_pattern and not has_year and len(citation) > 20:
                issues.append(f"Suspicious case citation format: {citation[:50]}")
        
        # Check for offline mode flag
        if research_output.get("offline_mode"):
            issues.append("Research was conducted in offline mode - human verification recommended")
        
        return issues
    
    def _determine_routing(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Determine routing based on scores and validation"""
        scores = result.get("scores", {})
        
        hallucination_risk = scores.get("hallucination_risk", 0)
        citation_density = scores.get("citation_density", 0)
        
        # Hard rules
        if hallucination_risk > 0:
            result["routing"] = "require_human_review"
            result["routing_reason"] = f"Hallucination risk detected: {hallucination_risk}"
        elif "child_urgent" in result.get("validation_issues", []) and citation_density < 2.0:
            result["routing"] = "require_human_review"
            result["routing_reason"] = "Child urgent flagged without sufficient citation evidence"
        else:
            # Calculate average score
            score_values = [v for k, v in scores.items() if k != "hallucination_risk"]
            avg_score = sum(score_values) / len(score_values) if score_values else 0
            
            if avg_score < 3.0:
                result["routing"] = "return_to_retrieval"
                result["routing_reason"] = f"Average quality score too low: {avg_score:.1f}"
            else:
                result["routing"] = "accept"
                result["routing_reason"] = f"Quality standards met: avg {avg_score:.1f}, hallucination risk {hallucination_risk}"
        
        return result
    
    def _validate_quality_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean quality gate output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            # Ensure scores exist with proper ranges
            required_scores = ["citation_density", "quote_fidelity", "jurisdiction_fit", 
                             "trauma_tone", "child_safety_calibration", "hallucination_risk"]
            
            if "scores" not in result:
                result["scores"] = {}
            
            for score_name in required_scores:
                if score_name not in result["scores"]:
                    result["scores"][score_name] = 3.0  # Default to middle score
                else:
                    # Clamp to 0-5 range
                    result["scores"][score_name] = max(0, min(5, float(result["scores"][score_name])))
            
            # Ensure remediation exists
            if "remediation" not in result:
                result["remediation"] = ["Review artifacts for citation quality", "Verify jurisdiction-specific legal references", "Check trauma-informed language usage"]
            
            # Ensure routing is valid
            valid_routing = ["accept", "return_to_retrieval", "require_human_review"]
            if result.get("routing") not in valid_routing:
                result["routing"] = "require_human_review"
                result["routing_reason"] = "Invalid routing determined"
            
            # Add provenance
            result["provenance"] = self._create_provenance("")
            
            return result
            
        except Exception as e:
            result["validation_error"] = str(e)
            return result
    
    def _create_default_evaluation(self, session_id: str, error_msg: str) -> Dict[str, Any]:
        """Create default evaluation for error cases"""
        return {
            "session_id": session_id,
            "scores": {
                "citation_density": 2.0,
                "quote_fidelity": 2.0,
                "jurisdiction_fit": 2.0,
                "trauma_tone": 3.0,
                "child_safety_calibration": 2.0,
                "hallucination_risk": 3.0  # Conservative high risk for errors
            },
            "remediation": [
                f"Quality evaluation failed: {error_msg}",
                "Manual review required due to evaluation error",
                "Verify all citations and legal references"
            ],
            "routing": "require_human_review",
            "routing_reason": f"Quality gate evaluation error: {error_msg}",
            "notes": "Automatic routing to human review due to quality gate failure",
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
