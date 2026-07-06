import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from the project root.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from backend.routes.ask import router as ask_router
from backend.routes.upload import router as upload_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Create the FastAPI application.
app = FastAPI(
    title="INDUS MIND API",
    description="Industrial RAG Assistant Backend",
    version="1.0.0",
)

# Register all API routes.
app.include_router(upload_router)
app.include_router(ask_router)


@app.get("/", summary="Home")
def home():
    """Health check endpoint."""

    return {
        "message": "Welcome to INDUS MIND",
        "status": "Backend Running Successfully",
    }


@app.get("/health", summary="Health")
def health():
    """Lightweight health endpoint for uptime checks."""

    return {"status": "ok"}
