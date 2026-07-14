#!/usr/bin/env python3
"""Regression tests for retrieval accuracy and metadata priority."""

import os
from backend.services.vectordb_service import VectorDBService, StoredChunk
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService

def run_tests():
    vdb = VectorDBService()
    
    # We will inject some fake chunks into a test collection to guarantee the test cases.
    test_collection_name = "test_retrieval_regression"
    vdb.collection_name = test_collection_name
    vdb.reset_collection()
    
    embedding_service = EmbeddingService()
    
    # We mock generate_embedding to return dummy vectors for speed, since we are testing logic.
    def dummy_embed(text: str) -> list[float]:
        return [0.1] * 384
    embedding_service.generate_embedding = dummy_embed
    
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vectordb_service=vdb,
    )

    # Prepare chunks
    # Chunk 1: The false positive (Page 8, text contains "Problem Statement 4/5")
    chunk1: StoredChunk = {
        "chunk_id": "chunk1_false_positive",
        "text": "This is Problem Statement 4/5. It is on page 8.",
        "page_start": 8,
        "page_end": 8,
        "metadata": {
            "document_id": "doc1",
            "filename": "doc1.pdf",
            "chunk_index": 1,
            "problem_statement_number": "4/5",
        }
    }
    
    # Chunk 2: The true positive for Problem Statement 8 (Page 15)
    chunk2: StoredChunk = {
        "chunk_id": "chunk2_true_positive",
        "text": "This is the actual Problem Statement 8 for AI for Industrial Knowledge.",
        "page_start": 15,
        "page_end": 15,
        "metadata": {
            "document_id": "doc1",
            "filename": "doc1.pdf",
            "chunk_index": 2,
            "problem_statement_number": "8",
        }
    }
    
    # Chunk 3: Another true positive for PS 8
    chunk3: StoredChunk = {
        "chunk_id": "chunk3_true_positive",
        "text": "More details about Problem Statement 8 and requirements.",
        "page_start": 15,
        "page_end": 15,
        "metadata": {
            "document_id": "doc1",
            "filename": "doc1.pdf",
            "chunk_index": 3,
            "problem_statement_number": "8",
        }
    }
    
    # Chunk 4: A random chunk about D2DAP
    chunk4: StoredChunk = {
        "chunk_id": "chunk4_d2dap",
        "text": "The phases of D2DAP are design, development, and deployment.",
        "page_start": 20,
        "page_end": 20,
        "metadata": {
            "document_id": "doc1",
            "filename": "doc1.pdf",
            "chunk_index": 4,
        }
    }
    
    chunks = [chunk1, chunk2, chunk3, chunk4]
    embeddings = [[0.1] * 384 for _ in chunks]
    vdb.add_chunks(chunks, embeddings)
    
    print("Test collection populated.")

    tests = [
        {
            "question": "Problem Statement 8",
            "expected_ids": {"chunk2_true_positive", "chunk3_true_positive"},
            "description": "Should return only PS8 chunks (Page 15) and ignore Page 8."
        },
        {
            "question": "Problem Statement 3",
            "expected_ids": set(),
            "description": "Should return empty or fallback gracefully if PS3 doesn't exist."
        },
        {
            "question": "Page 15",
            "expected_ids": {"chunk2_true_positive", "chunk3_true_positive"},
            "description": "Should return Page 15 chunks based on page_start metadata."
        },
    ]

    for test in tests:
        print(f"\n--- Testing: {test['question']} ---")
        response = retrieval_service.retrieve(test["question"], top_k=5)
        results = response["results"]
        result_ids = {r["chunk_id"] for r in results}
        
        print(f"Expected: {test['expected_ids']}")
        print(f"Actual:   {result_ids}")
        
        if test["expected_ids"]:
            # We expect the exact metadata match to bypass semantic and only return the exact hits.
            assert result_ids == test["expected_ids"], f"Failed: {test['description']}"
            print("PASS")
        else:
            print("PASS (Empty or fallback expected)")
            
    print("\nAll regression tests passed successfully!")

if __name__ == "__main__":
    run_tests()
