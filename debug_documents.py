#!/usr/bin/env python3
"""Debug script to check vector store documents and metadata."""

from backend.services.vectordb_service import VectorDBService
from backend.services.document_service import DocumentService

# Get all documents
vdb = VectorDBService()
doc_service = DocumentService(vdb)

print("\n=== Documents in Vector Store ===")
documents = doc_service.list_documents()
for doc in documents:
    print(f"  - {doc['document_id']}: {doc['filename']} ({doc['chunks']} chunks)")

print(f"\nTotal documents: {len(documents)}")
print(f"Total collection count: {vdb.collection.count()}")

# Get sample chunk metadata
if documents:
    first_doc_id = documents[0]['document_id']
    chunks = vdb.get_chunks(where={"document_id": {"$in": [first_doc_id]}})
    print(f"\n=== Sample Metadata for {first_doc_id} ===")
    if chunks:
        print(f"First chunk metadata: {chunks[0].get('metadata', {})}")
        print(f"\nNumber of chunks for {first_doc_id}: {len(chunks)}")
