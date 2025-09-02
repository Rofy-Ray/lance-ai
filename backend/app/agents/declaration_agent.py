import json
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Inches

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

class DeclarationAgent:
    """Judge-Ready Declaration / Affidavit Draft Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agent_id = "declaration"
    
    async def process(self, session_id: str, intake_output: Dict[str, Any], 
                     analysis_output: Dict[str, Any]) -> Dict[str, Any]:
        """Generate judge-ready declaration with numbered paragraphs and citations"""
        try:
            # Create declaration prompt
            prompt = self._create_declaration_prompt(session_id, intake_output, analysis_output)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_empty_response(session_id, "JSON parsing error")
            
            # Generate actual DOCX declaration
            if result.get("paragraphs"):
                declaration_path = await self._generate_declaration_docx(session_id, result)
                result["declaration_path"] = declaration_path
            
            # Validate output
            result = self._validate_declaration_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_empty_response(session_id, f"Declaration generation error: {str(e)}")
    
    def _create_declaration_prompt(self, session_id: str, intake_output: Dict[str, Any], 
                                 analysis_output: Dict[str, Any]) -> str:
        """Create declaration generation prompt"""
        
        # Extract key incidents with strong evidence
        strong_incidents = []
        for doc in intake_output.get("docs", []):
            for incident in doc.get("incidents", []):
                if (incident.get("confidence", 0) >= 0.7 and 
                    incident.get("quote_span") and 
                    len(incident.get("quote_span", "")) > 10):
                    
                    strong_incidents.append({
                        "incident_id": incident.get("incident_id"),
                        "date": incident.get("date"),
                        "summary": incident.get("summary"),
                        "quote": incident.get("quote_span"),
                        "doc_id": incident.get("doc_id"),
                        "page": incident.get("page"),
                        "line_range": incident.get("line_range"),
                        "wheel_tag": incident.get("wheel_tag")
                    })
        
        # Extract high-severity legal elements
        strong_elements = []
        for mapping in analysis_output.get("mappings", []):
            for element in mapping.get("legal_elements", []):
                if (element.get("severity", 0) >= 3 and 
                    element.get("confidence", 0) >= 0.6 and
                    element.get("fact_support")):
                    
                    strong_elements.append({
                        "element": element.get("element"),
                        "severity": element.get("severity"),
                        "fact_support": element.get("fact_support", [])[:2]  # Top 2 supporting facts
                    })
        
        return f"""Draft a 5-page declaration using only cited facts. Number paragraphs and add exhibit callouts.

Session ID: {session_id}

Strong Incidents with Evidence:
{json.dumps(strong_incidents, indent=2)}

High-Severity Legal Elements:
{json.dumps(strong_elements, indent=2)}

Generate a formal declaration with:

1. NUMBERED PARAGRAPHS (start from 1)
2. EACH PARAGRAPH must have supporting citations
3. EXHIBIT CALLOUTS in format (Ex. A, p.3:5-7)
4. CHRONOLOGICAL ORDER where possible
5. FORMAL LEGAL LANGUAGE appropriate for court

Structure:
- Background and standing (1-3 paragraphs)  
- Factual allegations (majority of content)
- Legal conclusions (final paragraphs)
- Prayer for relief

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "declaration_path": "/path/to/declaration.docx",
    "paragraphs": [
        {{
            "paragraph_number": 1,
            "date": "2023-01-15",
            "text": "I am the petitioner in this matter and have personal knowledge of the facts set forth herein.",
            "exhibit_callouts": ["Ex. A"],
            "quote_spans": [
                {{
                    "quote": "Supporting quote from evidence",
                    "doc_id": "doc_1", 
                    "page": 1,
                    "line_range": "5-7"
                }}
            ],
            "citations_present": true
        }}
    ],
    "n_pages": 5,
    "provenance": {{}}
}}

CRITICAL REQUIREMENTS:
- Every factual paragraph MUST cite supporting evidence
- Use formal declaration language: "I declare under penalty of perjury..."
- Remove any paragraphs lacking proper citations  
- Maximum 5 pages
- Include exhibit references for all factual claims"""
    
    async def _generate_declaration_docx(self, session_id: str, declaration_data: Dict[str, Any]) -> str:
        """Generate actual DOCX declaration file"""
        try:
            # Create session artifacts directory
            session_dir = Path(os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions")) / f"session_{session_id}"
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Create DOCX document
            doc = Document()
            
            # Header section
            header = doc.sections[0].header
            header_para = header.paragraphs[0]
            header_para.text = f"DECLARATION - Session {session_id}"
            
            # Title
            title = doc.add_heading('DECLARATION', 0)
            title.alignment = 1  # Center alignment
            
            doc.add_paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
            doc.add_paragraph()  # Spacing
            
            # Declaration body
            doc.add_paragraph("TO THE HONORABLE COURT:")
            doc.add_paragraph()
            
            # Add numbered paragraphs
            for para in declaration_data.get("paragraphs", []):
                para_num = para.get("paragraph_number", 0)
                para_text = para.get("text", "")
                
                # Create paragraph with number
                p = doc.add_paragraph()
                p.add_run(f"{para_num}. ").bold = True
                p.add_run(para_text)
                
                # Add exhibit callouts if present
                exhibit_callouts = para.get("exhibit_callouts", [])
                if exhibit_calls:
                    callout_text = " (" + ", ".join(exhibit_callouts) + ")"
                    p.add_run(callout_text).italic = True
                
                # Add spacing between paragraphs
                doc.add_paragraph()
            
            # Signature block
            doc.add_paragraph()
            doc.add_paragraph("I declare under penalty of perjury under the laws of the State that the foregoing is true and correct.")
            doc.add_paragraph()
            doc.add_paragraph(f"Executed on {datetime.now().strftime('%B %d, %Y')}.")
            doc.add_paragraph()
            doc.add_paragraph("_" * 40)
            doc.add_paragraph("Declarant")
            
            # Save document
            doc_path = artifacts_dir / "declaration.docx"
            doc.save(str(doc_path))
            
            return str(doc_path)
            
        except Exception as e:
            raise Exception(f"Failed to generate declaration DOCX: {str(e)}")
    
    def _validate_declaration_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean declaration output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            if "paragraphs" not in result:
                result["paragraphs"] = []
            
            # Validate paragraphs have proper citations
            validated_paragraphs = []
            for para in result.get("paragraphs", []):
                # Check if paragraph has citations
                has_quotes = para.get("quote_spans") and len(para["quote_spans"]) > 0
                has_valid_citations = False
                
                if has_quotes:
                    # Check if quotes have required fields
                    valid_quotes = []
                    for quote in para["quote_spans"]:
                        if all(field in quote for field in ["quote", "doc_id", "page", "line_range"]):
                            valid_quotes.append(quote)
                    
                    if valid_quotes:
                        para["quote_spans"] = valid_quotes
                        has_valid_citations = True
                
                # Mark citation status
                para["citations_present"] = has_valid_citations
                
                # Only include paragraphs with citations (except introduction/conclusion)
                para_text = para.get("text", "").lower()
                is_intro_conclusion = any(phrase in para_text for phrase in [
                    "i am", "i declare", "background", "standing", "knowledge", 
                    "prayer", "relief", "wherefore", "respectfully"
                ])
                
                if has_valid_citations or is_intro_conclusion:
                    validated_paragraphs.append(para)
                # Skip paragraphs without proper citations
            
            result["paragraphs"] = validated_paragraphs
            
            # Calculate estimated pages
            total_words = sum(len(para.get("text", "").split()) for para in validated_paragraphs)
            estimated_pages = max(1, total_words // 250)  # ~250 words per page
            result["n_pages"] = min(estimated_pages, 5)  # Cap at 5 pages
            
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
            "declaration_path": "",
            "paragraphs": [
                {
                    "paragraph_number": 1,
                    "text": f"Declaration generation failed: {error_msg}",
                    "exhibit_callouts": [],
                    "quote_spans": [],
                    "citations_present": False
                }
            ],
            "n_pages": 1,
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
