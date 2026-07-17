import asyncio
from backend.services.vectordb_service import VectorDBService
from backend.pipeline.ingestion_pipeline import IngestionPipeline
from backend.services.pdf_service import PDFService
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService

async def test():
    vectordb = VectorDBService()
    embedding_service = EmbeddingService()
    pdf_service = PDFService()
    retrieval_service = RetrievalService(embedding_service=embedding_service, vectordb_service=vectordb)
    ingestion = IngestionPipeline(pdf_service, embedding_service, vectordb)

    # 1. Ingest a document as admin
    # We will use the small dummy PDF test_document.pdf if we had one, but we'll mock ingestion or just use retrieval service on what's there.
    print("Testing RBAC Retrieval...")
    
    # We will just test if retrieve accepts the parameter and returns results
    # Since we didn't wipe the DB, the existing documents don't have an access_level field yet.
    # So `{"access_level": {"$in": ["public"]}}` will actually filter out everything that lacks the field if ChromaDB requires field existence.
    # Let's see what happens.
    
    # First, let's query as "public"
    print("\n--- Querying as 'public' ---")
    res1 = retrieval_service.retrieve(question="What is the problem statement?", top_k=2, user_role="public")
    print(f"Results for public: {len(res1.get('results', []))}")

    # Query as "admin"
    print("\n--- Querying as 'admin' ---")
    res2 = retrieval_service.retrieve(question="What is the problem statement?", top_k=2, user_role="admin")
    print(f"Results for admin: {len(res2.get('results', []))}")

if __name__ == "__main__":
    asyncio.run(test())
