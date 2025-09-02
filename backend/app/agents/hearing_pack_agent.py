import json
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Inches

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

class HearingPackAgent:
    """Evidence Matrix & Hearing Pack Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agent_id = "hearing_pack"
    
    async def process(self, session_id: str, intake_output: Dict[str, Any], 
                     analysis_output: Dict[str, Any], psla_output: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hearing pack with exhibit index and proposed findings"""
        try:
            # Create hearing pack prompt
            prompt = self._create_hearing_pack_prompt(session_id, intake_output, analysis_output, psla_output)
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_empty_response(session_id, "JSON parsing error")
            
            # Generate actual DOCX file
            if result.get("proposed_findings") and result.get("exhibit_map"):
                hearing_pack_path = await self._generate_hearing_pack_docx(session_id, result)
                result["hearing_pack_path"] = hearing_pack_path
            
            # Validate output
            result = self._validate_hearing_pack_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_empty_response(session_id, f"Hearing pack generation error: {str(e)}")
    
    def _create_hearing_pack_prompt(self, session_id: str, intake_output: Dict[str, Any], 
                                  analysis_output: Dict[str, Any], psla_output: Dict[str, Any]) -> str:
        """Create hearing pack generation prompt"""
        
        # Extract key findings from analysis
        key_elements = []
        for mapping in analysis_output.get("mappings", [])[:5]:  # Top 5 mappings
            for element in mapping.get("legal_elements", []):
                if element.get("severity", 0) >= 2 and element.get("confidence", 0) >= 0.6:
                    key_elements.append({
                        "element": element.get("element"),
                        "severity": element.get("severity"),
                        "fact_support": element.get("fact_support", [])
                    })
        
        # Extract PSLA findings
        psla_findings = []
        for finding in psla_output.get("findings", []):
            if finding.get("classification") in ["aggressive", "abusive"]:
                psla_findings.append({
                    "filing": finding.get("filing_id"),
                    "classification": finding.get("classification"),
                    "rationale": finding.get("rationale", "")[:200]
                })
        
        return f"""Draft a hearing_pack.docx: exhibit index, proposed findings of fact (each finding must cite a source). Do not introduce new facts.

Session ID: {session_id}

Key Legal Elements Identified:
{json.dumps(key_elements, indent=2)}

PSLA Findings:
{json.dumps(psla_findings, indent=2)}

Generate a comprehensive hearing pack with:

1. EXHIBIT INDEX - List all source documents as exhibits
2. PROPOSED FINDINGS OF FACT - Each finding must have direct citations
3. ISSUES FOR COURT - 3-5 key issues based on evidence
4. RECOMMENDED ORDERS - Specific relief requested with statutory basis

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "hearing_pack_path": "/path/to/hearing_pack.docx",
    "exhibit_map": [
        {{
            "exhibit_id": "Exhibit A",
            "file_name": "document1.pdf", 
            "purpose": "Evidence of coercive control pattern",
            "linked_elements": ["Pattern of Control and Dominance"]
        }}
    ],
    "proposed_findings": [
        {{
            "finding_id": "Finding 1",
            "text": "The evidence demonstrates a pattern of coercive control as shown in Exhibit A, page 3, lines 15-18.",
            "quote_spans": [
                {{
                    "quote": "Exact quote from evidence",
                    "doc_id": "doc_1",
                    "page": 3,
                    "line_range": "15-18"
                }}
            ],
            "corroborating_docs": ["doc_1", "doc_2"]
        }}
    ],
    "issues_for_court": [
        "Whether respondent engaged in pattern of post-separation abuse",
        "Whether modification of custody is warranted for child safety",
        "Whether supervised visitation should be ordered"
    ],
    "recommended_orders": [
        {{
            "order_text": "Order supervised visitation pending completion of domestic violence intervention program",
            "statutory_basis": "Family Code Section 3044"
        }}
    ],
    "notes": "Additional context or procedural notes",
    "provenance": {{}}
}}

CRITICAL REQUIREMENTS:
- Every proposed finding MUST cite specific evidence with exhibit, page, line
- Do not create findings without supporting quotes
- Maximum 20 pages of content
- Focus on strongest evidence only"""
    
    async def _generate_hearing_pack_docx(self, session_id: str, hearing_data: Dict[str, Any]) -> str:
        """Generate actual DOCX hearing pack file"""
        try:
            # Create session artifacts directory
            session_dir = Path(os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions")) / f"session_{session_id}"
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Create DOCX document
            doc = Document()
            
            # Title page
            title = doc.add_heading('HEARING PACK', 0)
            title.alignment = 1  # Center alignment
            
            doc.add_paragraph(f'Session ID: {session_id}')
            doc.add_paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
            doc.add_page_break()
            
            # Exhibit Index
            doc.add_heading('EXHIBIT INDEX', level=1)
            
            exhibit_table = doc.add_table(rows=1, cols=3)
            exhibit_table.style = 'Table Grid'
            hdr_cells = exhibit_table.rows[0].cells
            hdr_cells[0].text = 'Exhibit'
            hdr_cells[1].text = 'Document'
            hdr_cells[2].text = 'Purpose'
            
            for exhibit in hearing_data.get("exhibit_map", []):
                row_cells = exhibit_table.add_row().cells
                row_cells[0].text = exhibit.get("exhibit_id", "")
                row_cells[1].text = exhibit.get("file_name", "")
                row_cells[2].text = exhibit.get("purpose", "")
            
            doc.add_page_break()
            
            # Proposed Findings of Fact
            doc.add_heading('PROPOSED FINDINGS OF FACT', level=1)
            
            for i, finding in enumerate(hearing_data.get("proposed_findings", []), 1):
                # Finding paragraph with numbering
                finding_para = doc.add_paragraph()
                finding_para.add_run(f"{i}. ").bold = True
                finding_para.add_run(finding.get("text", ""))
                
                # Add citations
                if finding.get("quote_spans"):
                    citations_para = doc.add_paragraph()
                    citations_para.add_run("Citations: ").italic = True
                    for j, quote in enumerate(finding.get("quote_spans", [])):
                        if j > 0:
                            citations_para.add_run("; ")
                        citations_para.add_run(f"Ex. {quote.get('doc_id', 'Unknown')} p.{quote.get('page', 0)}:{quote.get('line_range', 'unknown')}")
                
                doc.add_paragraph()  # Spacing
            
            doc.add_page_break()
            
            # Issues for Court
            doc.add_heading('ISSUES FOR COURT', level=1)
            
            for i, issue in enumerate(hearing_data.get("issues_for_court", []), 1):
                doc.add_paragraph(f"{i}. {issue}")
            
            doc.add_page_break()
            
            # Recommended Orders
            doc.add_heading('RECOMMENDED ORDERS', level=1)
            
            for i, order in enumerate(hearing_data.get("recommended_orders", []), 1):
                order_para = doc.add_paragraph()
                order_para.add_run(f"{i}. ").bold = True
                order_para.add_run(order.get("order_text", ""))
                
                if order.get("statutory_basis"):
                    basis_para = doc.add_paragraph()
                    basis_para.add_run("Statutory Basis: ").italic = True
                    basis_para.add_run(order.get("statutory_basis"))
                
                doc.add_paragraph()  # Spacing
            
            # Notes section
            if hearing_data.get("notes"):
                doc.add_page_break()
                doc.add_heading('NOTES', level=1)
                doc.add_paragraph(hearing_data.get("notes"))
            
            # Save document
            doc_path = artifacts_dir / "hearing_pack.docx"
            doc.save(str(doc_path))
            
            return str(doc_path)
            
        except Exception as e:
            raise Exception(f"Failed to generate hearing pack DOCX: {str(e)}")
    
    def _validate_hearing_pack_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean hearing pack output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            # Validate proposed findings have citations
            validated_findings = []
            for finding in result.get("proposed_findings", []):
                if finding.get("quote_spans") and len(finding["quote_spans"]) > 0:
                    # Check if all quotes have required fields
                    valid_quotes = []
                    for quote in finding["quote_spans"]:
                        if all(field in quote for field in ["quote", "doc_id", "page", "line_range"]):
                            valid_quotes.append(quote)
                    
                    if valid_quotes:
                        finding["quote_spans"] = valid_quotes
                        finding["citations_present"] = True
                        validated_findings.append(finding)
                    else:
                        finding["citations_present"] = False
                        finding["validation_note"] = "Citations incomplete"
                else:
                    # Skip findings without proper citations
                    continue
            
            result["proposed_findings"] = validated_findings
            
            # Ensure exhibit map exists
            if "exhibit_map" not in result:
                result["exhibit_map"] = []
            
            if "issues_for_court" not in result:
                result["issues_for_court"] = []
            
            if "recommended_orders" not in result:
                result["recommended_orders"] = []
            
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
            "hearing_pack_path": "",
            "exhibit_map": [],
            "proposed_findings": [],
            "issues_for_court": [],
            "recommended_orders": [],
            "notes": f"Hearing pack generation failed: {error_msg}",
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
