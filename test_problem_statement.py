#!/usr/bin/env python3
"""Simulate the complete flow to debug the actual issue."""

from backend.services.vectordb_service import VectorDBService
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService

# Setup services
vdb = VectorDBService()
embedding_service = EmbeddingService()
retrieval_service = RetrievalService(
    embedding_service=embedding_service,
    vectordb_service=vdb,
)

# Simulate frontend conversion
def filenameToDocId(filename):
    """Frontend's filename to doc ID conversion."""
    if not filename:
        return ""
    basename = filename.split("/")[-1] if "/" in filename else filename
    lastDotIndex = basename.rfind(".")
    if lastDotIndex == -1:
        return basename
    return basename[:lastDotIndex]

# Get real filenames from database
chunks = vdb.get_chunks(limit=10)
unique_doc_ids = {}
for chunk in chunks:
    doc_id = chunk.get("metadata", {}).get("document_id")
    if doc_id and doc_id not in unique_doc_ids:
        unique_doc_ids[doc_id] = chunk.get("metadata", {}).get("filename")

print("\n=== Database Document IDs and Filenames ===")
for doc_id, filename in unique_doc_ids.items():
    print(f"\nStored doc_id: {doc_id}")
    print(f"Stored filename: {filename}")
    if filename:
        converted = filenameToDocId(filename)
        print(f"Frontend converts to: {converted}")
        print(f"Match: {'✓' if converted == doc_id else '✗ MISMATCH'}")

# Test with a question
print("\n" + "="*80)
print("=== Testing Question: 'Problem Statement 8?' ===")
print("="*80)

test_question = "Problem Statement 8?"

# Test 1: No filter
print("\nTest 1: No document filter")
response = retrieval_service.retrieve(question=test_question, top_k=5, document_ids=None)
print(f"  Results: {len(response['results'])} chunks")

# Test 2: With first document
if unique_doc_ids:
    first_doc_id = list(unique_doc_ids.keys())[0]
    print(f"\nTest 2: Filter by document '{first_doc_id}'")
    response = retrieval_service.retrieve(
        question=test_question,
        top_k=5,
        document_ids=[first_doc_id],
    )
    print(f"  Results: {len(response['results'])} chunks")
