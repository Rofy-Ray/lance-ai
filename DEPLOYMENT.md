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
- `LANGSMITH_API_KEY` = `your_langsmith_key` (optional)
- `PORT` = `8000`
- `HOST` = `0.0.0.0`

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
