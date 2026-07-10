import asyncio
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService
from backend.services.retrieval_service import RetrievalService

def main():
    emb = EmbeddingService()
    vdb = VectorDBService()
    ret = RetrievalService(embedding_service=emb, vectordb_service=vdb)
    
    question = 'How often should a centrifugal pump be lubricated?'
    print("Testing retrieve with question:", question)
    res = ret.retrieve(question=question, top_k=5)
    
    print(f'Number of retrieved results: {len(res.get("results", []))}')

if __name__ == "__main__":
    main()
