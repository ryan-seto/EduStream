from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.routes import auth, content, generate, publish, analytics
from app.database import engine, Base
from app.models import user, content as content_model  # Import models to register them

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="EduStream",
    description="Automated educational content generation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - allow multiple localhost ports for development
cors_origins = [
    settings.frontend_url,
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(content.router, prefix="/api/content", tags=["Content"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generation"])
app.include_router(publish.router, prefix="/api/publish", tags=["Publishing"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

# Serve static files (diagrams, audio, video)
output_dir = Path(settings.output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "EduStream"}


@app.get("/")
async def root():
    return {
        "message": "EduStream API",
        "docs": "/docs",
        "health": "/health",
    }
