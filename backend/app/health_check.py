"""
System Health Check Module
Validates all components are properly configured and working
"""

import os
import sys
from typing import Dict, List, Tuple
from pathlib import Path

class HealthCheck:
    """Performs comprehensive system health checks"""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        
    def check_environment_variables(self) -> Tuple[bool, str]:
        """Check required environment variables"""
        required_vars = [
            "OPENAI_API_KEY",
            "TAVILY_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            return False, f"Missing environment variables: {', '.join(missing)}"
        return True, "All environment variables configured"
    
    def check_dependencies(self) -> Tuple[bool, str]:
        """Check Python dependencies"""
        try:
            import fastapi
            import langchain
            import openai
            import faiss
            import reportlab
            import tavily
            return True, "All Python dependencies installed"
        except ImportError as e:
            return False, f"Missing dependency: {str(e)}"
    
    def check_file_structure(self) -> Tuple[bool, str]:
        """Check required files and directories exist"""
        base_path = Path(__file__).parent.parent.parent
        
        required_paths = [
            base_path / "agents" / "prompts" / "prompt_pack.json",
            base_path / "agents" / "data" / "wheel.json",
            base_path / "agents" / "schemas",
            base_path / "backend" / "app",
            base_path / "frontend" / "pages",
            base_path / "frontend" / "components"
        ]
        
        missing = []
        for path in required_paths:
            if not path.exists():
                missing.append(str(path))
        
        if missing:
            return False, f"Missing paths: {', '.join(missing[:3])}..."
        return True, "All required files and directories present"
    
    def check_agents(self) -> Tuple[bool, str]:
        """Check all agents can be imported"""
        try:
            from app.agents.intake_agent import IntakeAgent
            from app.agents.analysis_agent import AnalysisAgent
            from app.agents.psla_agent import PSLAAgent
            from app.agents.hearing_pack_agent import HearingPackAgent
            from app.agents.declaration_agent import DeclarationAgent
            from app.agents.client_letter_agent import ClientLetterAgent
            from app.agents.research_agent import ResearchAgent
            from app.agents.quality_gate_agent import QualityGateAgent
            return True, "All 8 agents loaded successfully"
        except ImportError as e:
            return False, f"Agent import failed: {str(e)}"
    
    def check_vector_database(self) -> Tuple[bool, str]:
        """Check FAISS vector database functionality"""
        try:
            from app.faiss_store import FAISSStore
            # Don't initialize as it requires API key
            return True, "FAISS vector database module available"
        except ImportError as e:
            return False, f"FAISS import failed: {str(e)}"
    
    def check_pdf_generation(self) -> Tuple[bool, str]:
        """Check PDF generation capability"""
        try:
            from app.pdf_generator import PDFGenerator
            from app.prompt_optimizer import PromptOptimizer
            return True, "PDF generation and prompt optimization ready"
        except ImportError as e:
            return False, f"PDF/Prompt module failed: {str(e)}"
    
    def run_all_checks(self) -> Dict[str, any]:
        """Run all health checks"""
        checks = [
            ("Environment Variables", self.check_environment_variables),
            ("Python Dependencies", self.check_dependencies),
            ("File Structure", self.check_file_structure),
            ("Agent Modules", self.check_agents),
            ("Vector Database", self.check_vector_database),
            ("PDF Generation", self.check_pdf_generation)
        ]
        
        results = []
        for name, check_func in checks:
            try:
                passed, message = check_func()
                if passed:
                    self.checks_passed.append(name)
                    results.append({"check": name, "status": "✅", "message": message})
                else:
                    self.checks_failed.append(name)
                    results.append({"check": name, "status": "❌", "message": message})
            except Exception as e:
                self.checks_failed.append(name)
                results.append({"check": name, "status": "❌", "message": f"Error: {str(e)}"})
        
        return {
            "total_checks": len(checks),
            "passed": len(self.checks_passed),
            "failed": len(self.checks_failed),
            "results": results,
            "system_ready": len(self.checks_failed) == 0
        }
    
    def print_report(self):
        """Print health check report"""
        report = self.run_all_checks()
        
        print("\n" + "="*60)
        print("LANCE AI SYSTEM HEALTH CHECK")
        print("="*60)
        
        for result in report["results"]:
            print(f"{result['status']} {result['check']}: {result['message']}")
        
        print("\n" + "-"*60)
        print(f"Summary: {report['passed']}/{report['total_checks']} checks passed")
        
        if report["system_ready"]:
            print("✅ System is ready for operation!")
        else:
            print("⚠️  System requires configuration. Check failed items above.")
        print("="*60 + "\n")
        
        return report["system_ready"]

if __name__ == "__main__":
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    health = HealthCheck()
    health.print_report()
