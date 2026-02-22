# EduStream AI

Automated educational content generation platform for creating short-form engineering education videos.

## Features

- **AI Script Generation**: Uses Gemini API (with mock fallback) to generate quiz-style educational scripts
- **Diagram Generation**: Matplotlib-based engineering diagrams (beam analysis, circuits, etc.)
- **Google OAuth**: Secure authentication with whitelisted email access
- **Content Management**: Dashboard for viewing and managing generated content

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS + TanStack Query
- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL
- **AI**: Google Gemini API
- **Diagrams**: Matplotlib

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (installed locally, not Docker)

## Setup

### 1. PostgreSQL Database

PostgreSQL runs as a Windows service. Verify it's running:
```powershell
Get-Service -Name 'postgresql*'
```

Create the database (first time only):
```powershell
& "D:\Coding\PostgresSQL\bin\psql.exe" -U postgres -c "CREATE USER edustream WITH PASSWORD 'edustream_dev';"
& "D:\Coding\PostgresSQL\bin\psql.exe" -U postgres -c "CREATE DATABASE edustream OWNER edustream;"
```

### 2. Backend Setup

```powershell
cd backend

# Create virtual environment (first time)
python -m venv venv

# Activate venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env example and configure
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```powershell
cd frontend

# Install dependencies
npm install
```

### 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID
3. Add authorized JavaScript origins:
   - `http://localhost:5173`
   - `http://localhost:5174`
   - `http://localhost:5175`
4. Copy Client ID to `backend/.env` as `GOOGLE_CLIENT_ID`

## Running Locally

### Start Backend (Terminal 1)
```powershell
cd "d:\Coding\Projects\Social Media Bot\backend"
venv\Scripts\python -m uvicorn app.main:app --reload
```
Backend runs at: http://localhost:8000

### Start Frontend (Terminal 2)
```powershell
cd "d:\Coding\Projects\Social Media Bot\frontend"
npm run dev
```
Frontend runs at: http://localhost:5173

## Environment Variables

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://edustream:edustream_dev@localhost:5432/edustream

# JWT Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id

# Allowed email addresses (comma-separated)
ALLOWED_EMAILS=user@gmail.com

# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Output directories
OUTPUT_DIR=./output
TEMP_DIR=./temp

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173
```

## Project Structure

```
Social Media Bot/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── models/          # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   │   ├── ai_generator.py    # AI script generation
│   │   │   ├── diagram_gen.py     # Matplotlib diagrams
│   │   │   ├── tts_service.py     # Text-to-speech (disabled)
│   │   │   └── video_builder.py   # Video assembly (disabled)
│   │   ├── config.py        # Settings
│   │   ├── database.py      # DB connection
│   │   └── main.py          # FastAPI app
│   ├── output/              # Generated files
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── contexts/        # React contexts
│   │   ├── pages/           # Page components
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## API Endpoints

- `POST /api/auth/google` - Google OAuth login
- `GET /api/auth/me` - Get current user
- `GET /api/content/` - List all content
- `GET /api/content/topics` - List topics
- `POST /api/content/topics` - Create topic
- `POST /api/generate/single` - Generate content for a topic
- `GET /api/generate/status/{id}` - Check generation status

## Content Generation Pipeline

1. **Script Generation** - AI creates structured quiz content (hook, options, answer, explanation)
2. **Diagram Generation** - Matplotlib renders engineering diagram based on script description
3. *(Disabled)* **TTS Audio** - Edge TTS converts narration to speech
4. *(Disabled)* **Video Assembly** - MoviePy combines diagram + audio into vertical video

## Troubleshooting

### PostgreSQL not running
```powershell
Start-Service -Name 'postgresql-x64-18'
```

### Database connection refused
Ensure PostgreSQL service is running and credentials in `.env` match.

### Google OAuth "origin not allowed"
Add `http://localhost:5173` to authorized JavaScript origins in Google Cloud Console.

### Gemini API errors
The system falls back to mock data if Gemini API fails. Check your API key in `.env`.
