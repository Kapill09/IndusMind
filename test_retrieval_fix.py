import asyncio
import logging
from backend.pipeline.rag_pipeline import RAGPipeline
from backend.services.retrieval_service import RetrievalService
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService
from backend.services.llm_service import LLMService

logging.basicConfig(level=logging.INFO)

def test_rag():
    print("Initializing pipeline...")
    embedding_service = EmbeddingService()
    vectordb = VectorDBService()
    llm_service = LLMService()
    retrieval_service = RetrievalService(embedding_service, vectordb)
    
    pipeline = RAGPipeline(retrieval_service, llm_service, embedding_service)
    
    print("Running test query...")
    # Using the exact problem query
    response = pipeline.ask("Compare D2DAP and MAKA.", top_k=5)
    
    print("\n--- RESULTS ---")
    print(f"Success: {response.get('success')}")
    print(f"Confidence: {response.get('confidence')}")
    print(f"Chunks Sent to Gemini: {response.get('context_chunks')}")
    print(f"Answer: {response.get('answer')[:200]}...")

if __name__ == "__main__":
    test_rag()
