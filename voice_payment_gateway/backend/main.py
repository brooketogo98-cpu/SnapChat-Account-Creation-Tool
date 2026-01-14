from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import engine, Base, get_db
from app.routers import sessions, payments, auth, voice
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    yield
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Voice Payment Gateway API",
    description="Backend for voice‑based payment processing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Call Sessions"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice Interaction"])

@app.get("/")
async def root():
    return {"message": "Voice Payment Gateway API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)