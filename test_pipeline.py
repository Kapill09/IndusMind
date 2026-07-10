import asyncio
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService
from backend.services.retrieval_service import RetrievalService
from backend.services.llm_service import LLMService
from backend.pipeline.rag_pipeline import RAGPipeline

def main():
    emb = EmbeddingService()
    vdb = VectorDBService()
    ret = RetrievalService(embedding_service=emb, vectordb_service=vdb)
    llm = LLMService()
    
    pipeline = RAGPipeline(retrieval_service=ret, llm_service=llm)
    
    question = 'How often should a centrifugal pump be lubricated?'
    print("Testing pipeline with question:", question)
    res = pipeline.ask(question=question, top_k=5)
    
    print(f'Number of context chunks: {res["context_chunks"]}')
    print(f'Sources: {len(res["sources"])}')

if __name__ == "__main__":
    main()
