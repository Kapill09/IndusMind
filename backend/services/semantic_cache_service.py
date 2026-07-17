import logging
from time import perf_counter
from typing import Optional, Dict, Any
import json
import uuid
import hashlib

import chromadb
from chromadb.config import Settings
import backend.config as config
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class SemanticCacheService:
    """Provides semantic caching for LLM responses using ChromaDB."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.client = chromadb.PersistentClient(path=getattr(config, "CHROMA_PATH", "./data/chroma"))
        self.collection = self.client.get_or_create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"}
        )
        # Threshold for semantic equivalence (0.98 means almost identical phrasing)
        self.similarity_threshold = 0.98

    def _get_scope_hash(self, document_ids: list[str] | None) -> str:
        """Generate a deterministic hash for the document scope."""
        if not document_ids:
            return "global"
        sorted_ids = sorted(document_ids)
        return hashlib.md5(",".join(sorted_ids).encode()).hexdigest()

    def get(self, query: str, document_ids: list[str] | None = None) -> Optional[Dict[str, Any]]:
        """Retrieve a cached response if semantically similar to the query."""
        try:
            scope_hash = self._get_scope_hash(document_ids)
            query_embedding = self.embedding_service.generate_embedding(query, is_query=True)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
                where={"scope_hash": scope_hash},
                include=["documents", "metadatas", "distances"]
            )

            if results and results.get("distances") and results["distances"][0]:
                distance = results["distances"][0][0]
                similarity = 1.0 - distance
                if similarity >= self.similarity_threshold:
                    metadata = results["metadatas"][0][0]
                    logger.info("Semantic Cache HIT for query: '%s' (similarity: %.4f, scope: %s)", query, similarity, scope_hash)
                    try:
                        return json.loads(metadata.get("response", "{}"))
                    except json.JSONDecodeError:
                        logger.error("Failed to decode cached response.")
                        
            logger.info("Semantic Cache MISS for query: '%s' (scope: %s)", query, scope_hash)
            return None
        except Exception as exc:
            logger.warning("Semantic Cache failed to GET: %s", exc)
            return None

    def set(self, query: str, document_ids: list[str] | None, response: Dict[str, Any]) -> None:
        """Store a generated response in the semantic cache."""
        try:
            scope_hash = self._get_scope_hash(document_ids)
            query_embedding = self.embedding_service.generate_embedding(query, is_query=True)
            cache_id = str(uuid.uuid4())
            
            self.collection.add(
                ids=[cache_id],
                embeddings=[query_embedding],
                documents=[query],
                metadatas=[{
                    "response": json.dumps(response),
                    "scope_hash": scope_hash
                }]
            )
            logger.info("Semantic Cache SET for query: '%s' (scope: %s)", query, scope_hash)
        except Exception as exc:
            logger.warning("Semantic Cache failed to SET: %s", exc)
