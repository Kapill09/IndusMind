import json
from backend.services.retrieval_service import RetrievalService
from backend.services.embedding_service import EmbeddingService
from backend.services.vectordb_service import VectorDBService

rs = RetrievalService(EmbeddingService(), VectorDBService())
res = rs.retrieve('What is Problem Statement 8?', top_k=5, document_ids=None)
print(json.dumps(res, indent=2))
