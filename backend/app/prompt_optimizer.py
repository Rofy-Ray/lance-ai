"""
Prompt Optimizer Module
Enhances and standardizes prompts across all agents for better output quality
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptOptimizer:
    """Optimizes and standardizes prompts for all agents"""
    
    def __init__(self):
        self.prompt_templates = self._load_prompt_templates()
        self.output_examples = self._load_output_examples()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load optimized prompt templates"""
        return {
            "system_context": """You are a legal document analysis expert assistant. 
Your responses must be precise, evidence-based, and professionally formatted.
Always cite specific sources and maintain high accuracy standards.""",
            
            "evidence_instruction": """When analyzing evidence:
1. Quote directly from source documents with page/line references
2. Verify all facts against original documents
3. Maintain chronological order where applicable
4. Use confidence scores (0.0-1.0) for uncertain findings
5. Cross-reference multiple sources when available""",
            
            "output_format": """Structure your output as follows:
- Use clear section headers
- Number all lists and findings
- Include citations in format: [Doc ID, Page X, Lines Y-Z]
- Provide confidence scores for each claim
- Separate facts from analysis/conclusions""",
            
            "quality_checks": """Before finalizing output, verify:
✓ All claims have supporting evidence
✓ Citations are accurate and complete
✓ No speculation without clear disclaimer
✓ Professional tone maintained throughout
✓ Output follows specified JSON schema exactly"""
        }
    
    def _load_output_examples(self) -> Dict[str, Any]:
        """Load example outputs for few-shot learning"""
        return {
            "incident_example": {
                "incident_id": "INC-001",
                "date": "2023-01-15",
                "incident_type": "emotional_abuse",
                "description": "Respondent sent threatening messages",
                "direct_quotes": ["You'll regret this", "I know where you live"],
                "doc_id": "DOC-001",
                "page": 3,
                "line_range": "15-18",
                "confidence": 0.95,
                "wheel_tags": ["intimidation", "threats"]
            },
            "finding_example": {
                "finding_number": 1,
                "finding": "Respondent engaged in pattern of coercive control",
                "evidence": [
                    {
                        "source": "Petitioner Declaration",
                        "citation": "[Ex. A, p.2:10-15]",
                        "quote": "He monitored all my communications"
                    },
                    {
                        "source": "Text Messages",
                        "citation": "[Ex. B, p.5-7]",
                        "quote": "Multiple messages demanding location updates"
                    }
                ],
                "legal_basis": "Cal. Fam. Code § 6320",
                "confidence": 0.88
            }
        }
    
    def optimize_prompt(self, base_prompt: str, agent_type: str, 
                       include_examples: bool = True) -> str:
        """Optimize a prompt with better structure and examples"""
        
        optimized = f"""{self.prompt_templates['system_context']}

{self.prompt_templates['evidence_instruction']}

TASK INSTRUCTIONS:
{base_prompt}

{self.prompt_templates['output_format']}
"""
        
        if include_examples and agent_type in self.output_examples:
            optimized += f"""
EXAMPLE OUTPUT FORMAT:
{json.dumps(self.output_examples.get(agent_type, {}), indent=2)}
"""
        
        optimized += f"""
{self.prompt_templates['quality_checks']}

Remember: Accuracy and evidence-based analysis are paramount. 
Only include information you can verify from the provided documents."""
        
        return optimized
    
    def add_chain_of_thought(self, prompt: str) -> str:
        """Add chain-of-thought reasoning to prompt"""
        cot_instruction = """
REASONING PROCESS:
Before generating your final output, work through this analysis:
1. Identify key facts and evidence from documents
2. Verify quotes and citations are accurate
3. Analyze patterns and connections between incidents
4. Assess severity and legal implications
5. Formulate conclusions based on evidence
6. Structure output according to requirements

Show your reasoning briefly before the final JSON output.
"""
        return prompt + cot_instruction
    
    def add_validation_rules(self, prompt: str, agent_type: str) -> str:
        """Add specific validation rules for each agent type"""
        
        validation_rules = {
            "intake": """
VALIDATION REQUIREMENTS:
- Each incident must have: date, type, description, and source citation
- Direct quotes must be exact matches from documents
- Confidence scores required for all findings
- Maximum 20 incidents per document""",
            
            "hearing_pack": """
VALIDATION REQUIREMENTS:
- Minimum 5 proposed findings of fact
- Each finding must cite at least 2 sources
- Include exhibit index with all documents
- Recommended orders must cite legal authority""",
            
            "declaration": """
VALIDATION REQUIREMENTS:
- Paragraphs must be numbered sequentially
- Each paragraph limited to 1-2 key facts
- All facts must have exhibit citations
- Include proper declaration language/oath""",
            
            "client_letter": """
VALIDATION REQUIREMENTS:
- Reading level must be Grade 7-9
- No legal jargon without explanation
- Include safety resources and contacts
- Clear disclaimer about legal advice"""
        }
        
        if agent_type in validation_rules:
            return prompt + validation_rules[agent_type]
        return prompt
    
    def create_few_shot_prompt(self, task: str, examples: List[Dict[str, Any]]) -> str:
        """Create few-shot learning prompt with examples"""
        
        prompt = f"""Given these examples of high-quality outputs:

"""
        for i, example in enumerate(examples[:3], 1):
            prompt += f"""Example {i}:
Input: {example.get('input', 'N/A')}
Output: {json.dumps(example.get('output', {}), indent=2)}

"""
        
        prompt += f"""Now complete this task:
{task}

Generate output following the same format and quality standards as the examples."""
        
        return prompt
    
    def add_error_recovery(self, prompt: str) -> str:
        """Add error recovery instructions"""
        
        error_instructions = """
ERROR HANDLING:
If you encounter any of these issues:
- Missing or unclear information: Note as "Information not available" with explanation
- Conflicting evidence: Present both versions with sources
- Damaged/illegible text: Mark as "[illegible]" and work with available content
- Insufficient evidence: Clearly state limitations and confidence level

Always provide the most complete output possible despite any limitations.
"""
        return prompt + error_instructions
    
    def optimize_for_model(self, prompt: str, model_name: str = "gpt-4") -> str:
        """Optimize prompt for specific model characteristics"""
        
        if "gpt-4" in model_name:
            # GPT-4 optimizations
            prompt = prompt.replace("Generate", "Please generate")
            prompt = prompt.replace("must", "should")
            prompt += "\n\nTake your time to ensure accuracy and completeness."
        
        elif "gpt-3.5" in model_name:
            # GPT-3.5 optimizations - more explicit instructions
            prompt = prompt.replace("appropriate", "appropriate (professional and formal)")
            prompt = prompt.replace("relevant", "directly relevant")
            prompt += "\n\nBe concise but complete. Focus on the most important information."
        
        return prompt
    
    def create_structured_prompt(self, agent_type: str, context: Dict[str, Any]) -> str:
        """Create a fully structured and optimized prompt for an agent"""
        
        base_structure = f"""
═══════════════════════════════════════════════════════════════
AGENT: {agent_type.upper()} ANALYSIS
═══════════════════════════════════════════════════════════════

SESSION CONTEXT:
• Session ID: {context.get('session_id', 'N/A')}
• Document Count: {context.get('doc_count', 0)}
• Analysis Stage: {context.get('stage', 'Initial')}

{self.prompt_templates['system_context']}

═══════════════════════════════════════════════════════════════
PRIMARY OBJECTIVE:
{context.get('objective', 'Analyze documents and generate required output')}

{self.prompt_templates['evidence_instruction']}

═══════════════════════════════════════════════════════════════
INPUT DATA:
{json.dumps(context.get('input_data', {}), indent=2)[:2000]}

═══════════════════════════════════════════════════════════════
REQUIRED OUTPUT FORMAT:
{context.get('output_schema', 'See schema specification')}

{self.prompt_templates['output_format']}

{self.prompt_templates['quality_checks']}

═══════════════════════════════════════════════════════════════
"""
        return base_structure
