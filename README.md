# Lance AI - Document Analysis Pipeline

A comprehensive document analysis system that uses an 8-agent pipeline to analyze legal documents for domestic violence cases.

## Overview

Lance AI analyzes uploaded legal documents through an 8-agent pipeline to identify patterns of post-separation abuse, generate court-ready artifacts, and provide plain-language guidance to clients. All data is processed temporarily with automatic deletion after 1 hour.

## ✨ Recent Improvements

### PDF Generation (v2.0)
- ✅ All artifacts now generated as professional PDFs using ReportLab
- ✅ Structured formatting with headers, sections, and page breaks
- ✅ Automatic fallback to text files on PDF generation failure

### Enhanced Agent Intelligence
- ✅ Vector database integration for evidence-based analysis
- ✅ Prompt optimization module for consistent high-quality outputs
- ✅ Chain-of-thought reasoning for better decision making
- ✅ Validation rules and error recovery mechanisms

### System Optimization
- ✅ Health check module for system diagnostics
- ✅ Cleaned up dependencies and removed duplicates
- ✅ Improved error handling and logging

## Features

- **8-Agent Pipeline**: Specialized agents for different analysis tasks
- **Document Processing**: Support for PDF, DOCX, and text files
- **Vector Database**: FAISS-based document search and retrieval
- **Real-time Progress**: Live updates during document analysis
- **Professional Artifacts**: PDF-formatted hearing packs, declarations, and client letters
- **Web Search**: Integrated Tavily API for legal research
- **Prompt Optimization**: Intelligent prompt enhancement for better outputs

## Architecture

- **Frontend**: Next.js + Tailwind CSS (deployed to Vercel)
- **Backend**: Python FastAPI + LangChain agents (deployed to Render/Fly)
- **AI Models**: OpenAI gpt-5-mini (generation) + text-embedding-small (embeddings)
- **Vector Store**: FAISS (in-memory)
- **Session Storage**: Ephemeral SQLite
- **Observability**: LangSmith

## Monorepo Structure

```
/lance_ai
├── /frontend          # Next.js app
├── /backend           # FastAPI + agents
├── /agents            # Prompts, schemas, data
├── /infra             # Deployment configs
└── README.md
```

## Development

### Running Tests

```bash
cd backend
pytest
```

### Code Structure

```
lance_ai/
├── backend/
│   ├── app/
│   │   ├── agents/          # 8 specialized analysis agents
│   │   ├── parsers/         # Document parsing utilities
│   │   ├── agents_runner.py # Main orchestration
│   │   ├── faiss_store.py   # Vector database
│   │   ├── pdf_generator.py # PDF artifact generation
│   │   ├── prompt_optimizer.py # Prompt enhancement
│   │   ├── health_check.py  # System diagnostics
│   │   └── main.py          # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── pages/               # Next.js pages
│   ├── components/          # React components
│   └── package.json
└── agents/
    ├── prompts/            # Agent prompt templates
    ├── schemas/            # Output JSON schemas
    └── data/               # Reference data (abuse wheel)
```

### Key Modules

- **AgentsRunner**: Orchestrates the 8-agent pipeline
- **FAISSStore**: Manages vector embeddings and search
- **PDFGenerator**: Creates professional PDF artifacts
- **PromptOptimizer**: Enhances prompts for better outputs
- **HealthCheck**: Validates system configuration, data

## Installation

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Health Check

Verify system configuration:

```bash
python app/health_check.py
```

### Quick Start

### Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Create a `.env` file in the backend directory:

```bash
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
LANGSMITH_API_KEY=your_langsmith_key  # Optional
LANGSMITH_TRACING=true  # Optional
SESSION_TTL_SECONDS=3600
FAISS_DATA_DIR=/tmp/faiss
UPLOAD_TMP_DIR=/tmp/lance/sessions
DB_PATH=sqlite:///tmp/lance/sessions.sqlite
DEPLOYMENT_ENV=staging
```

## Privacy & Safety

- All documents processed temporarily in memory
- Automatic session deletion after 1 hour
- No persistent storage of PII or document content
- Manual delete option with confirmation
- Trauma-informed analysis approach

## Legal Disclaimer

Lance AI is an AI-assisted analysis tool. It does not provide legal advice and is not a substitute for professional legal counsel.
