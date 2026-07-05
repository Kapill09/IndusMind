from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from backend.routes.upload import router as upload_router

# Create the FastAPI application
app = FastAPI()

# Connect the upload routes to this FastAPI app.
app.include_router(upload_router)


@app.get("/")                       #Known as Route 
def home():                         # Only runs when / is executed
    return {
        "message": "Welcome to INDUS MIND 🚀",
        "status": "Backend Running Successfully"
    }
