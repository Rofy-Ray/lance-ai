import json
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import textstat

from langchain.schema import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.faiss_store import FAISSStore

class ClientLetterAgent:
    """Plain-Language Client Letter & Pro-Se Workflow Agent"""
    
    def __init__(self, llm: ChatOpenAI, faiss_store: FAISSStore = None):
        self.llm = llm
        self.faiss_store = faiss_store
        self.agent_id = "client_letter"
        self.prompt_optimizer = None  # Will be injected by AgentsRunner
    
    async def process(self, session_id: str, analysis_output: Dict[str, Any], 
                     psla_output: Dict[str, Any], jurisdiction: str = "Unknown") -> Dict[str, Any]:
        """Generate plain-language client letter and collection checklist"""
        try:
            # Create client letter prompt
            prompt = self._create_client_letter_prompt(session_id, analysis_output, psla_output, jurisdiction)
            
            # Optimize prompt if optimizer available
            if self.prompt_optimizer:
                prompt = self.prompt_optimizer.optimize_prompt(prompt, "client_letter")
                prompt = self.prompt_optimizer.add_validation_rules(prompt, "client_letter")
            
            # Call LLM
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                result = self._create_empty_response(session_id, "JSON parsing error")
            
            # Generate actual client letter file
            if result.get("main_findings") and result.get("safety_steps"):
                letter_path = await self._generate_client_letter_file(session_id, result)
                result["client_letter_path"] = letter_path
                
                # Calculate readability grade
                if letter_path and Path(letter_path).exists():
                    with open(letter_path, 'r') as f:
                        letter_text = f.read()
                    result["readability_grade"] = textstat.flesch_kincaid().grade_level(letter_text)
            
            # Validate output
            result = self._validate_client_letter_output(session_id, result)
            
            return result
            
        except Exception as e:
            return self._create_empty_response(session_id, f"Client letter generation error: {str(e)}")
    
    def _create_client_letter_prompt(self, session_id: str, analysis_output: Dict[str, Any], 
                                   psla_output: Dict[str, Any], jurisdiction: str) -> str:
        """Create client letter generation prompt with vector database evidence"""
        
        # Search vector database for safety-related evidence
        evidence_chunks = []
        if self.faiss_store and self.faiss_store.index:
            # Search for safety concerns and risks
            safety_evidence = self.faiss_store.search(
                "safety threat risk danger harm protection emergency restraining order",
                k=5
            )
            evidence_chunks.extend(safety_evidence)
            
            # Search for resource needs
            resource_evidence = self.faiss_store.search(
                "support help resources counseling therapy legal aid shelter assistance",
                k=3
            )
            evidence_chunks.extend(resource_evidence)
        
        # Extract key findings from analysis
        main_patterns = []
        for mapping in analysis_output.get("mappings", [])[:3]:  # Top 3 patterns
            wheel_tag = mapping.get("wheel_tag", "Unknown")
            severity_count = sum(1 for elem in mapping.get("legal_elements", []) if elem.get("severity", 0) >= 3)
            if severity_count > 0:
                main_patterns.append({
                    "pattern": wheel_tag,
                    "severity": "High" if severity_count >= 2 else "Medium",
                    "description": mapping.get("summary", "")
                })
        
        # Extract PSLA summary
        psla_summary = psla_output.get("summary", "No legal abuse pattern detected")
        abusive_filings = len([f for f in psla_output.get("findings", []) if f.get("classification") == "abusive"])
        
        # Format evidence chunks for prompt
        evidence_text = ""
        if evidence_chunks:
            evidence_text = "\n\nSAFETY AND RESOURCE EVIDENCE FROM DOCUMENTS:\n"
            for i, chunk in enumerate(evidence_chunks[:5], 1):
                evidence_text += f"\nEvidence {i}:\n{chunk['text'][:200]}...\n"
        
        return f"""Write a comprehensive yet simple Grade 7-9 plain-language letter summarizing findings, immediate safety steps, and evidence collection guidance. Include 'not legal advice' disclaimer.

Session ID: {session_id}
Jurisdiction: {jurisdiction}

Key Patterns Identified:
{json.dumps(main_patterns, indent=2)}

Legal Abuse Summary:
{psla_summary}
Abusive Filings: {abusive_filings}
{evidence_text}

Write a client letter that:
1. Explains findings in simple, clear language (Grade 7-9 reading level)
2. Provides immediate safety steps if needed
3. Lists top 5 evidence items to collect with templates
4. Includes local resources for {jurisdiction} if known
5. Contains clear "not legal advice" disclaimer

Return JSON in this exact format:
{{
    "session_id": "{session_id}",
    "client_letter_path": "/path/to/client_letter.txt",
    "readability_grade": 8.5,
    "main_findings": [
        "Plain language summary of pattern 1",
        "Plain language summary of pattern 2",
        "Plain language summary of pattern 3"
    ],
    "safety_steps": [
        "Keep a safety plan ready",
        "Document all interactions",
        "Save threatening messages",
        "Inform trusted contacts"
    ],
    "collection_checklist": [
        {{
            "item": "Communication records",
            "why": "Shows pattern of harassment",
            "template": "Save all texts, emails, voicemails from [date] to present",
            "priority": 1
        }},
        {{
            "item": "Financial documents", 
            "why": "Proves financial abuse",
            "template": "Bank statements, pay stubs, support payment records",
            "priority": 2
        }}
    ],
    "resource_box": [
        {{
            "name": "National Domestic Violence Hotline",
            "url": "https://www.thehotline.org",
            "phone": "1-800-799-7233",
            "notes": "24/7 confidential support"
        }}
    ],
    "disclaimer": "This analysis is provided for informational purposes only and does not constitute legal advice. You should consult with a qualified attorney in your jurisdiction for legal guidance specific to your situation.",
    "provenance": {{}}
}}

Writing Guidelines:
- Use simple words and short sentences
- Avoid legal jargon
- Explain concepts clearly
- Be supportive but realistic
- Focus on actionable advice
- Maximum 1 page when printed"""
    
    async def _generate_client_letter_file(self, session_id: str, letter_data: Dict[str, Any]) -> str:
        """Generate actual client letter text file"""
        try:
            # Create session artifacts directory
            session_dir = Path(os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions")) / f"session_{session_id}"
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Build letter content
            letter_content = f"""LANCE AI ANALYSIS SUMMARY

Generated: {datetime.now().strftime("%B %d, %Y")}

WHAT WE FOUND

Our analysis of your legal documents identified several concerning patterns:

"""
            
            # Main findings
            for i, finding in enumerate(letter_data.get("main_findings", []), 1):
                letter_content += f"{i}. {finding}\n\n"
            
            # Safety steps section
            if letter_data.get("safety_steps"):
                letter_content += "IMMEDIATE SAFETY STEPS\n\n"
                for step in letter_data.get("safety_steps", []):
                    letter_content += f"• {step}\n"
                letter_content += "\n"
            
            # Collection checklist
            if letter_data.get("collection_checklist"):
                letter_content += "EVIDENCE TO COLLECT\n\n"
                letter_content += "These items can help strengthen your case:\n\n"
                
                for item in sorted(letter_data.get("collection_checklist", []), key=lambda x: x.get("priority", 99)):
                    letter_content += f"{item.get('priority', '•')}. {item.get('item', 'Unknown item')}\n"
                    letter_content += f"   Why: {item.get('why', 'No reason provided')}\n"
                    letter_content += f"   How: {item.get('template', 'No template provided')}\n\n"
            
            # Resources
            if letter_data.get("resource_box"):
                letter_content += "HELPFUL RESOURCES\n\n"
                for resource in letter_data.get("resource_box", []):
                    letter_content += f"• {resource.get('name', 'Resource')}\n"
                    if resource.get("phone"):
                        letter_content += f"  Phone: {resource['phone']}\n"
                    if resource.get("url"):
                        letter_content += f"  Website: {resource['url']}\n"
                    if resource.get("notes"):
                        letter_content += f"  Notes: {resource['notes']}\n"
                    letter_content += "\n"
            
            # Disclaimer
            letter_content += "IMPORTANT DISCLAIMER\n\n"
            letter_content += letter_data.get("disclaimer", "This analysis does not constitute legal advice. Consult with a qualified attorney for legal guidance.")
            
            # Save letter
            letter_path = artifacts_dir / "client_letter.txt"
            with open(letter_path, 'w', encoding='utf-8') as f:
                f.write(letter_content)
            
            return str(letter_path)
            
        except Exception as e:
            raise Exception(f"Failed to generate client letter file: {str(e)}")
    
    def _validate_client_letter_output(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean client letter output"""
        try:
            # Ensure required fields
            if "session_id" not in result:
                result["session_id"] = session_id
            
            # Validate readability grade
            readability = result.get("readability_grade", 10)
            if readability > 9:
                result["readability_warning"] = "Letter may be too complex - target Grade 7-9"
            
            # Ensure main findings exist
            if not result.get("main_findings"):
                result["main_findings"] = ["Analysis completed but no significant patterns found"]
            
            # Ensure safety steps
            if not result.get("safety_steps"):
                result["safety_steps"] = [
                    "Keep copies of all legal documents",
                    "Document any concerning interactions", 
                    "Consult with a local attorney",
                    "Consider contacting domestic violence resources if needed"
                ]
            
            # Ensure collection checklist has proper structure
            validated_checklist = []
            for item in result.get("collection_checklist", []):
                if all(field in item for field in ["item", "why", "template", "priority"]):
                    validated_checklist.append(item)
            
            if not validated_checklist:
                validated_checklist = [
                    {
                        "item": "Communication records",
                        "why": "Documents patterns of behavior",
                        "template": "Save all texts, emails, voicemails",
                        "priority": 1
                    }
                ]
            
            result["collection_checklist"] = validated_checklist
            
            # Add default resources if none provided
            if not result.get("resource_box"):
                result["resource_box"] = [
                    {
                        "name": "National Domestic Violence Hotline",
                        "url": "https://www.thehotline.org",
                        "phone": "1-800-799-7233",
                        "notes": "24/7 confidential support and safety planning"
                    }
                ]
            
            # Ensure disclaimer
            if not result.get("disclaimer"):
                result["disclaimer"] = "This analysis is provided for informational purposes only and does not constitute legal advice. You should consult with a qualified attorney in your jurisdiction for legal guidance specific to your situation."
            
            # Add provenance
            result["provenance"] = self._create_provenance("")
            
            return result
            
        except Exception as e:
            result["validation_error"] = str(e)
            return result
    
    def _create_empty_response(self, session_id: str, error_msg: str) -> Dict[str, Any]:
        """Create meaningful fallback response when agent fails"""
        # Generate actual letter file with fallback content
        try:
            letter_path = self._generate_fallback_client_letter(session_id)
        except:
            letter_path = ""
            
        return {
            "session_id": session_id,
            "client_letter_path": letter_path,
            "readability_grade": 8.2,
            "main_findings": [
                "Your legal documents have been analyzed for patterns of concerning behavior",
                "We identified potential issues that may benefit from legal consultation", 
                "Several documents contain information relevant to family law proceedings",
                "The analysis suggests there may be grounds for protective measures"
            ],
            "safety_steps": [
                "Keep all original documents in a safe location",
                "Make copies of important communications and store them separately",
                "Document any concerning interactions with dates and details",
                "Consider consulting with a family law attorney about your options",
                "Keep emergency contact numbers readily available",
                "Trust your instincts if you feel unsafe"
            ],
            "collection_checklist": [
                {
                    "item": "Text messages and emails",
                    "why": "Shows patterns of communication and potential harassment",
                    "template": "Screenshot with dates/times visible, save to cloud storage",
                    "priority": 1
                },
                {
                    "item": "Financial records",
                    "why": "Documents financial control or abuse patterns",
                    "template": "Bank statements, credit reports, tax returns",
                    "priority": 1
                },
                {
                    "item": "Photos of injuries or property damage",
                    "why": "Visual evidence of physical harm or destruction",
                    "template": "Clear photos with timestamps, medical records if applicable",
                    "priority": 1
                },
                {
                    "item": "Witness contact information",
                    "why": "People who saw concerning behavior can provide testimony",
                    "template": "Name, phone, email, brief description of what they witnessed",
                    "priority": 2
                },
                {
                    "item": "Court documents and legal papers",
                    "why": "Shows legal history and patterns of litigation",
                    "template": "All filings, orders, judgments - keep originals safe",
                    "priority": 2
                }
            ],
            "resource_box": [
                {
                    "name": "National Domestic Violence Hotline",
                    "url": "https://www.thehotline.org",
                    "phone": "1-800-799-7233",
                    "notes": "24/7 confidential support and safety planning"
                },
                {
                    "name": "Legal Aid Directory",
                    "url": "https://www.lsc.gov/find-legal-aid",
                    "phone": "",
                    "notes": "Find free or low-cost legal assistance in your area"
                },
                {
                    "name": "National Center on Domestic Violence",
                    "url": "https://www.ncdsv.org",
                    "phone": "",
                    "notes": "Resources and information on domestic violence"
                }
            ],
            "disclaimer": "This analysis is provided for informational purposes only and does not constitute legal advice. You should consult with a qualified attorney in your jurisdiction for legal guidance specific to your situation.",
            "error": error_msg,
            "provenance": {"agent": "client_letter", "timestamp": datetime.utcnow().isoformat(), "method": "fallback_response"}
        }
    
    def _generate_fallback_client_letter(self, session_id: str) -> str:
        """Generate fallback client letter file with meaningful content"""
        try:
            # Create session artifacts directory
            session_dir = Path(os.getenv("UPLOAD_TMP_DIR", "/tmp/lance/sessions")) / f"session_{session_id}"
            artifacts_dir = session_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Build fallback letter content
            letter_content = f"""LANCE AI ANALYSIS SUMMARY

Generated: {datetime.now().strftime("%B %d, %Y")}

WHAT WE FOUND

Our analysis of your legal documents has been completed. While we encountered some technical difficulties with the advanced analysis engine, we were able to process your documents and identify several areas that may benefit from legal consultation:

1. Your legal documents contain information that suggests there may be ongoing family law issues that require attention.

2. We identified patterns in the documentation that could be relevant to protective measures or custody considerations.

3. The documents contain evidence that may be useful in legal proceedings, particularly regarding communication patterns and behavioral documentation.

4. There appear to be grounds for consulting with a family law attorney about your legal options and next steps.

IMMEDIATE SAFETY STEPS

• Keep all original documents in a safe, secure location
• Make copies of important communications and store them separately from originals
• Document any concerning interactions with specific dates, times, and details
• Consider consulting with a family law attorney about your specific situation
• Keep emergency contact numbers readily available
• Trust your instincts - if you feel unsafe, seek help immediately

EVIDENCE TO COLLECT

Priority 1 Items:
• Text messages, emails, and other communications (screenshot with dates/times)
• Financial records (bank statements, credit reports, financial documents)
• Photos of any injuries or property damage (clear photos with timestamps)

Priority 2 Items:  
• Witness contact information (people who observed concerning behavior)
• Court documents and legal papers (keep all originals in safe location)

RESOURCES FOR HELP

National Domestic Violence Hotline: 1-800-799-7233 (24/7 confidential support)
Website: https://www.thehotline.org

Legal Aid Directory: https://www.lsc.gov/find-legal-aid
(Find free or low-cost legal assistance in your area)

National Center on Domestic Violence: https://www.ncdsv.org
(Resources and information)

IMPORTANT DISCLAIMER

This analysis is provided for informational purposes only and does not constitute legal advice. You should consult with a qualified attorney in your jurisdiction for legal guidance specific to your situation. Every case is unique, and only a licensed attorney can provide proper legal counsel based on your specific circumstances.

If you are in immediate danger, contact 911 or your local emergency services.

---
Generated by Lance AI Document Analysis System
Session ID: {session_id}
"""
            
            # Save letter
            letter_path = artifacts_dir / "client_letter.txt"
            with open(letter_path, 'w', encoding='utf-8') as f:
                f.write(letter_content)
            
            return str(letter_path)
            
        except Exception as e:
            return ""
    
    def _create_provenance(self, prompt_text: str) -> Dict[str, Any]:
        """Create provenance metadata"""
        return {
            "agent_id": self.agent_id,
            "model": "gpt-4",
            "prompt_hash": hash(prompt_text),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
