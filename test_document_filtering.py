#!/usr/bin/env python3
"""Test script to verify document filtering works correctly."""

from backend.services.vectordb_service import VectorDBService
from backend.services.document_service import DocumentService
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService

# Get all documents
vdb = VectorDBService()
doc_service = DocumentService(vdb)
documents = doc_service.list_documents()

print("\n=== Test Document Filtering ===\n")

if not documents:
    print("No documents found in the database")
    exit(1)

# Use the first document ID
first_doc_id = documents[0]['document_id']
print(f"Testing with document_id: {first_doc_id}")
print(f"Filename: {documents[0]['filename']}")

# Test retrieval with document filter
embedding_service = EmbeddingService()
retrieval_service = RetrievalService(
    embedding_service=embedding_service,
    vectordb_service=vdb,
)

test_question = "Problem Statement"

print(f"\n--- Test 1: Search WITHOUT document filter ---")
try:
    response_all = retrieval_service.retrieve(
        question=test_question,
        top_k=3,
        document_ids=None,
    )
    print(f"Results without filter: {len(response_all['results'])} chunks found")
except Exception as e:
    print(f"Error: {e}")

print(f"\n--- Test 2: Search WITH document filter (document_id={first_doc_id}) ---")
try:
    response_filtered = retrieval_service.retrieve(
        question=test_question,
        top_k=3,
        document_ids=[first_doc_id],
    )
    print(f"Results with filter: {len(response_filtered['results'])} chunks found")
    
    if response_filtered['results']:
        print(f"\nFirst result metadata:")
        for key, value in response_filtered['results'][0]['metadata'].items():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Frontend Test Cases ===\n")
# Simulate what the frontend does

def filenameToDocId_OLD(filename: str | None) -> str:
    """Old (broken) implementation."""
    if not filename:
        return ""
    parts = filename.split("/").pop().split(".") if filename else []
    parts.pop() if parts else None
    return ".".join(parts) if parts else filename

def filenameToDocId_NEW(filename: str | None) -> str:
    """New (fixed) implementation."""
    if not filename:
        return ""
    basename = filename.split("/").pop() or filename
    lastDotIndex = basename.rfind(".")
    if lastDotIndex == -1:
        return basename
    return basename[:lastDotIndex]

for doc in documents:
    filename = doc['filename']
    doc_id = doc['document_id']
    
    old_result = filenameToDocId_OLD(filename)
    new_result = filenameToDocId_NEW(filename)
    
    print(f"Filename: {filename}")
    print(f"  Expected (from DB): {doc_id}")
    print(f"  Old logic result:   {old_result} {'✓' if old_result == doc_id else '✗ WRONG'}")
    print(f"  New logic result:   {new_result} {'✓' if new_result == doc_id else '✗ WRONG'}")
    print()
