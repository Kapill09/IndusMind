from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.routes.ask import router as ask_router
from backend.routes.upload import router as upload_router

# Load environment variables from the project root.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

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
        "message": "Welcome to INDUS MIND 🚀",
        "status": "Backend Running Successfully",
    }