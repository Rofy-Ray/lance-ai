# Lance AI

A privacy-first AI application that detects post-separation abuse and coercive control patterns in family law documents.

## Overview

Lance AI analyzes uploaded legal documents through an 8-agent pipeline to identify patterns of post-separation abuse, generate court-ready artifacts, and provide plain-language guidance to clients. All data is processed temporarily with automatic deletion after 1 hour.

## Architecture

- **Frontend**: Next.js + Tailwind CSS (deployed to Vercel)
- **Backend**: Python FastAPI + LangChain agents (deployed to Render/Fly)
- **AI Models**: OpenAI gpt-5-nano (generation) + text-embedding-small (embeddings)
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

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

```bash
OPENAI_API_KEY=your_openai_key
LANGSMITH_API_KEY=your_langsmith_key
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
