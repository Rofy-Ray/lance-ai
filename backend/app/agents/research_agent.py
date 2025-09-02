import json
from typing import Dict, Any, List
from datetime import datetime

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

class ResearchAgent:
    """Research Retrieval & Verification Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agent_id = "research"
    
    async def process(self, session_id: str, jurisdiction: str, time_horizon_years: int = 5) -> Dict[str, Any]:
        """Find relevant legal authorities for jurisdiction"""
        try:
            # Create research prompt
            prompt = self._create_research_prompt(session_id, jurisdiction, time_horizon_years)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_offline_response(session_id, jurisdiction)
            
            # Validate output
            result = self._validate_research_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_offline_response(session_id, jurisdiction, f"Research error: {str(e)}")
    
    def _create_research_prompt(self, session_id: str, jurisdiction: str, time_horizon_years: int) -> str:
        """Create research prompt"""
        
        current_year = datetime.now().year
        start_year = current_year - time_horizon_years
        
        return f"""Find top statutes/cases/practice guides on coercive control and PSLA in {jurisdiction} (past {time_horizon_years} years). Provide pinpoint quotes and relevance.

Session ID: {session_id}
Jurisdiction: {jurisdiction}
Time Frame: {start_year}-{current_year}

Research Areas:
1. Coercive Control Statutes
2. Post-Separation Abuse Case Law
3. Family Violence Prevention Laws
4. Custody Modification Standards for Abuse
5. Legal System Abuse Prevention

For each authority found, provide:
- Type (statute, case, practice guide, other)
- Full legal citation
- Relevant quote (maximum 25 words)
- Pinpoint citation if applicable
- Relevance explanation (1 line)
- URL if available

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "authorities": [
        {{
            "type": "statute",
            "citation": "Family Code Section 3044",
            "quote": "Rebuttable presumption against custody to perpetrator of domestic violence",
            "pinpoint": "subsection (a)",
            "relevance": "Directly applicable to custody modification based on abuse findings",
            "jurisdiction": "{jurisdiction}",
            "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044&lawCode=FAM",
            "notes": "Key statute for family law practitioners"
        }},
        {{
            "type": "case",
            "citation": "Smith v. Jones, 123 Cal.App.5th 456 (2023)",
            "quote": "Pattern of coercive control sufficient for custody modification",
            "pinpoint": "at 462",
            "relevance": "Establishes precedent for coercive control in custody decisions",
            "jurisdiction": "{jurisdiction}",
            "url": null,
            "notes": "Recent appellate decision"
        }}
    ],
    "summary": "Research summary with key takeaways for {jurisdiction}",
    "provenance": {{}}
}}

IMPORTANT: 
- If you cannot access current legal databases, return needs_human_review in summary
- Provide only accurate citations - do not invent case names or statute numbers
- Focus on most relevant and recent authorities
- Include both state and federal law where applicable"""
    
    def _validate_research_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean research output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            if "authorities" not in result:
                result["authorities"] = []
            
            # Validate authorities have required fields
            validated_authorities = []
            for authority in result.get("authorities", []):
                if all(field in authority for field in ["type", "citation", "quote", "relevance", "jurisdiction"]):
                    # Ensure type is valid
                    if authority["type"] not in ["statute", "case", "practice_guide", "other"]:
                        authority["type"] = "other"
                    
                    # Truncate long quotes
                    if len(authority["quote"]) > 100:
                        authority["quote"] = authority["quote"][:97] + "..."
                    
                    validated_authorities.append(authority)
            
            result["authorities"] = validated_authorities
            
            # Ensure summary exists
            if not result.get("summary"):
                auth_count = len(validated_authorities)
                if auth_count > 0:
                    result["summary"] = f"Found {auth_count} relevant legal authorities for the jurisdiction."
                else:
                    result["summary"] = "No specific legal authorities found - recommend human review for jurisdiction-specific research."
            
            # Add provenance
            result["provenance"] = self._create_provenance("")
            
            return result
            
        except Exception as e:
            result["validation_error"] = str(e)
            return result
    
    def _create_offline_response(self, session_id: str, jurisdiction: str, error_msg: str = None) -> Dict[str, Any]:
        """Create response when online research is not available"""
        
        # Provide general authorities that commonly exist
        general_authorities = []
        
        if "california" in jurisdiction.lower() or "ca" in jurisdiction.lower():
            general_authorities = [
                {
                    "type": "statute",
                    "citation": "Family Code Section 3044",
                    "quote": "Rebuttable presumption against custody to domestic violence perpetrator",
                    "pinpoint": "(a)",
                    "relevance": "Key statute for custody decisions involving domestic violence",
                    "jurisdiction": jurisdiction,
                    "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044",
                    "notes": "Requires human verification of current language"
                },
                {
                    "type": "statute", 
                    "citation": "Family Code Section 6340",
                    "quote": "Coercive control as form of abuse in restraining orders",
                    "pinpoint": "(a)",
                    "relevance": "Defines coercive control for family law purposes",
                    "jurisdiction": jurisdiction,
                    "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=6340",
                    "notes": "Added coercive control definition in recent years"
                }
            ]
        else:
            # Generic federal/model authorities
            general_authorities = [
                {
                    "type": "statute",
                    "citation": "Violence Against Women Act (VAWA), 34 U.S.C. § 12291",
                    "quote": "Federal framework for domestic violence prevention and response",
                    "pinpoint": "et seq.",
                    "relevance": "Federal law applicable across all jurisdictions",
                    "jurisdiction": "Federal",
                    "url": "https://www.law.cornell.edu/uscode/text/34/12291",
                    "notes": "Federal statute - check state implementation"
                }
            ]
        
        summary = f"Offline mode - provided general authorities for {jurisdiction}. "
        if error_msg:
            summary += f"Error: {error_msg}. "
        summary += "Human review recommended for jurisdiction-specific and current research."
        
        return {
            "session_id": session_id,
            "authorities": general_authorities,
            "summary": summary,
            "needs_human_review": True,
            "offline_mode": True,
            "provenance": self._create_provenance("")
        }
    
    def _create_provenance(self, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata"""
        return {
            "agent_id": self.agent_id,
            "model": "gpt-4",
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "research_method": "llm_generated"
        }
