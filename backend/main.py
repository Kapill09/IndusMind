import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from the project root.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from backend.routes.analytics import router as analytics_router
from backend.routes.ask import router as ask_router
from backend.routes.documents import api_documents_router, router as documents_router
from backend.routes.health import router as health_router
from backend.routes.knowledge_graph import router as knowledge_graph_router
from backend.routes.context_graph import router as context_graph_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:5176",
        "http://localhost:5176",
        "https://mozilla.github.io",
    ],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API routes.
app.include_router(upload_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.include_router(api_documents_router)
app.include_router(analytics_router)
app.include_router(health_router)
app.include_router(knowledge_graph_router)
app.include_router(context_graph_router)


@app.get("/", summary="Home")
def home():
    """Health check endpoint."""

    return {
        "message": "Welcome to INDUS MIND",
        "status": "Backend Running Successfully",
    }
