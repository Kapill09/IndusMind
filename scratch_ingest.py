import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.pipeline.ingestion_pipeline import IngestionPipeline
from backend.services.pdf_service import PDFService
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService
from backend.services.bm25_service import BM25Service

def main():
    print("Initializing services...")
    pdf_service = PDFService()
    embedding_service = EmbeddingService()
    vectordb_service = VectorDBService()
    bm25_service = BM25Service()
    
    pipeline = IngestionPipeline(
        pdf_service=pdf_service,
        embedding_service=embedding_service,
        vectordb_service=vectordb_service,
        bm25_service=bm25_service
    )
    
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        print(f"Directory not found: {raw_dir}")
        return
        
    for pdf_path in raw_dir.glob("*.pdf"):
        print(f"Ingesting: {pdf_path.name}")
        try:
            summary = pipeline.ingest_document(pdf_path)
            print(f"Success! {summary}")
        except Exception as e:
            print(f"Failed to ingest {pdf_path.name}: {e}")

if __name__ == "__main__":
    main()
