import time
from backend.services.vectordb_service import VectorDBService, StoredChunk
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService
from backend.services.llm_service import LLMService
from backend.pipeline.rag_pipeline import RAGPipeline
import backend.config as config

def test_regression():
    print("========================================")
    print("RERANKER REGRESSION TESTS")
    print("========================================")
    
    # Force reranker enabled for this test
    config.ENABLE_RERANKER = True
    config.RERANK_TOP_N = 20
    config.FINAL_TOP_K = 2
    config.RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    vdb = VectorDBService()
    vdb.collection_name = "test_reranker_collection"
    vdb.reset_collection()
    
    embedding_service = EmbeddingService()
    
    # Mock embedding
    def dummy_embed(text: str) -> list[float]:
        return [0.1] * 384
    embedding_service.generate_embedding = dummy_embed
    
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vectordb_service=vdb,
    )
    
    # Provide dummy chunks
    chunks = [
        {
            "chunk_id": "chunk_ps8_1",
            "text": "This is Problem Statement 8 regarding industrial automation.",
            "page_start": 1,
            "page_end": 1,
            "metadata": {"problem_statement_number": "8", "document_id": "test_doc", "filename": "test.pdf", "chunk_index": 1}
        },
        {
            "chunk_id": "chunk_ps8_2",
            "text": "Another description of Problem Statement 8.",
            "page_start": 2,
            "page_end": 2,
            "metadata": {"problem_statement_number": "8", "document_id": "test_doc", "filename": "test.pdf", "chunk_index": 2}
        },
        {
            "chunk_id": "chunk_ps4",
            "text": "This is Problem Statement 4 regarding predictive maintenance.",
            "page_start": 3,
            "page_end": 3,
            "metadata": {"problem_statement_number": "4", "document_id": "test_doc", "filename": "test.pdf", "chunk_index": 3}
        },
        {
            "chunk_id": "chunk_d2dap",
            "text": "D2DAP Authentication details are explained here.",
            "page_start": 4,
            "page_end": 4,
            "metadata": {"document_id": "test_doc", "filename": "test.pdf", "chunk_index": 4}
        },
        {
            "chunk_id": "chunk_lockout",
            "text": "What is Lockout Tagout? It is a safety procedure.",
            "page_start": 5,
            "page_end": 5,
            "metadata": {"document_id": "test_doc", "filename": "test.pdf", "chunk_index": 5}
        }
    ]
    
    embeddings = [[0.1] * 384 for _ in chunks]
    vdb.add_chunks(chunks, embeddings)
    
    class DummyLLMService(LLMService):
        def generate_answer(self, question, retrieved_chunks):
            return {"answer": "Dummy answer", "model": "test-model"}
            
    rag_pipeline = RAGPipeline(
        retrieval_service=retrieval_service,
        llm_service=DummyLLMService(),
    )
    
    QUESTIONS = [
        ("Problem Statement 8", ["chunk_ps8_1", "chunk_ps8_2"]),
        ("D2DAP Authentication", ["chunk_d2dap"]),
        ("What is Lockout Tagout?", ["chunk_lockout"]),
    ]
    
    total_latency = 0
    for q, expected in QUESTIONS:
        print(f"\n[Test] Question: {q}")
        start = time.time()
        
        try:
            response = rag_pipeline.ask(question=q, top_k=5)
            latency = int((time.time() - start) * 1000)
            total_latency += latency
            
            results = response.get("retrieval", {}).get("results", [])
            retrieved_ids = [c["chunk_id"] for c in results]
            
            print(f"Status: SUCCESS | Latency: {latency}ms | Chunks: {len(results)}")
            for i, chunk in enumerate(results[:2]):
                metadata = chunk.get("metadata", {})
                print(f"  #{i+1} [ID: {chunk.get('chunk_id')}] - "
                      f"Reranker: {metadata.get('reranker_score', 'N/A')} | "
                      f"Final: {metadata.get('final_score', 'N/A')} | "
                      f"Structured: {metadata.get('structured_score', 'N/A')}")
                      
            # Verify top chunk matches expectations
            if expected:
                if results and results[0]["chunk_id"] in expected:
                    print("  -> Assertion PASS: Correct chunk retrieved")
                else:
                    print(f"  -> Assertion FAIL: Expected one of {expected}, got {retrieved_ids}")
                    
        except Exception as e:
            print(f"Status: FAILED | Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n========================================")
    print(f"Tests Completed | Avg Latency: {total_latency / len(QUESTIONS):.0f}ms")
    print("========================================")

if __name__ == "__main__":
    test_regression()
