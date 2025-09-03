# Deployment Configuration

## Vercel Frontend Deployment

### Environment Variables to Set in Vercel Dashboard:

**Required:**
- `NEXT_PUBLIC_API_URL` = `https://your-backend-url.onrender.com` (or your backend deployment URL)

**Optional:**
- `NODE_ENV` = `production`

### Backend Deployment (Render/Railway recommended)

**Required Environment Variables:**
- `OPENAI_API_KEY` = `sk-proj-...` (your OpenAI API key)
- `TAVILY_API_KEY` = `your_tavily_key`
- `LANGSMITH_API_KEY` = `your_langsmith_key` (optional)

**Render Configuration:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** `backend`

**Important:** Render automatically sets the `PORT` environment variable. The start command must bind to `0.0.0.0` and use `$PORT` to work correctly.

## Deployment Strategy

### Frontend (Vercel)
- Deploys automatically from `/frontend` directory
- Serves Next.js static files and API routes
- Uses `NEXT_PUBLIC_API_URL` to connect to backend

### Backend (Render/Railway)
- Deploys FastAPI application
- Exposes API endpoints at `/api/*`
- Handles file uploads and AI processing

### CORS Configuration
Backend already configured to accept requests from any origin in production.
