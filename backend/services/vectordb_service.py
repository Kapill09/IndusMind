import logging
import os
from pathlib import Path
from typing import Any, TypedDict

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from backend.config import CHROMA_PATH, COLLECTION_NAME


DEFAULT_CHROMA_PATH = Path(CHROMA_PATH)
if not DEFAULT_CHROMA_PATH.is_absolute():
    DEFAULT_CHROMA_PATH = Path(__file__).resolve().parents[2] / DEFAULT_CHROMA_PATH
logger = logging.getLogger(__name__)


class StoredChunk(TypedDict):
    """Chunk shape expected by the vector database service."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]


class VectorSearchResult(TypedDict):
    """One nearest-neighbor result returned from ChromaDB."""

    chunk_id: str
    text: str
    distance: float | None
    metadata: dict[str, Any]


class VectorDBServiceError(Exception):
    """Base exception for all ChromaDB service errors."""


class VectorDBValidationError(VectorDBServiceError):
    """Raised when chunks, embeddings, or query inputs are invalid."""


class VectorDBOperationError(VectorDBServiceError):
    """Raised when ChromaDB cannot complete a storage operation."""


class VectorDBService:
    """Store and search INDUS MIND chunk vectors in ChromaDB.

    This service only owns vector database operations. It does not generate
    embeddings, call OpenAI, build prompts, perform retrieval orchestration, or
    produce LLM answers.

    Args:
        persist_directory: Directory where ChromaDB stores persistent data.
        collection_name: Name of the ChromaDB collection to use.
        client: Optional Chroma client, useful for tests.
    """

    def __init__(
        self,
        *,
        persist_directory: str | Path = DEFAULT_CHROMA_PATH,
        collection_name: str = COLLECTION_NAME,
        client: Any | None = None,
        auto_backfill_access_level: bool = True,
    ) -> None:
        # Keep these values on the class so all methods use the same database.
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        try:
            # PersistentClient stores vectors on disk instead of in memory.
            self.client = client or chromadb.PersistentClient(path=str(self.persist_directory))

            # A single collection keeps industrial knowledge in one searchable index.
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "INDUS MIND industrial knowledge chunks"},
                embedding_function=None,
            )
            if auto_backfill_access_level:
                self.backfill_missing_access_level()
        except Exception as exc:
            raise VectorDBOperationError("Failed to initialize ChromaDB collection.") from exc

    def add_chunks(self, chunks: list[StoredChunk], embeddings: list[list[float]]) -> int:
        """Store chunk texts, metadata, and precomputed embeddings in ChromaDB.

        Args:
            chunks: Text chunks produced by the chunking stage.
            embeddings: Embedding vectors produced by the embedding stage.

        Returns:
            Number of chunks stored.

        Raises:
            VectorDBValidationError: If chunks and embeddings are invalid.
            VectorDBOperationError: If ChromaDB cannot store the data.
        """

        self._validate_chunks_and_embeddings(chunks, embeddings)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str | int | float | bool]] = []

        for chunk in chunks:
            metadata = self._build_metadata(chunk)
            ids.append(chunk["chunk_id"])
            documents.append(chunk["text"])
            metadatas.append(metadata)

        try:
            # Upsert makes ingestion safe to rerun for the same document.
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise VectorDBOperationError("Failed to store chunks in ChromaDB.") from exc

        logger.info(
            "Chroma upsert completed: collection=%s chunks=%s",
            self.collection_name,
            len(chunks),
        )
        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search ChromaDB using a precomputed query embedding.

        Args:
            query_embedding: Embedding vector for the user query.
            top_k: Maximum number of nearest chunks to return.
            where: Optional Chroma metadata filter.

        Returns:
            A list of nearest ChromaDB records with text, metadata, and distance.

        Raises:
            VectorDBValidationError: If the query embedding or top_k is invalid.
            VectorDBOperationError: If ChromaDB cannot complete the query.
        """

        self._validate_embedding(query_embedding, field_name="query_embedding")
        if top_k <= 0:
            raise VectorDBValidationError("top_k must be greater than 0.")

        try:
            # Query by embedding only; embedding generation belongs to another service.
            query_args: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_args["where"] = where

            logger.info("=" * 80)
            logger.info("WHERE FILTER = %s", where)
            logger.info("QUERY ARGS = %s", query_args)
            logger.info("=" * 80)
            logger.info("=" * 80)
            logger.info("CHROMA QUERY")
            logger.info("WHERE FILTER = %s", where)
            logger.info("=" * 80)
            
            results = self.collection.query(**query_args)
            
            logger.info("Returned %d chunks", len(results["ids"][0]))

            for i in range(min(5, len(results["ids"][0]))):
                meta = results["metadatas"][0][i]
                logger.info(
                    "[%d] document_id=%s filename=%s",
                    i + 1,
                    meta.get("document_id"),
                    meta.get("filename"),
                )

            logger.info("Returned %d results", len(results.get("ids", [[]])[0]))

        except Exception as exc:
            raise VectorDBOperationError("Failed to search ChromaDB collection.") from exc

        formatted = self._format_search_results(results)
        logger.info(
            "Chroma search completed: collection=%s top_k=%s results=%s filtered=%s",
            self.collection_name,
            top_k,
            len(formatted),
            bool(where),
        )
        return formatted

    def get_chunks(self, limit: int | None = None, where: dict[str, Any] | None = None) -> list[VectorSearchResult]:
        """Return stored chunks with text and metadata for local hybrid scoring."""

        if limit is not None and limit <= 0:
            raise VectorDBValidationError("limit must be greater than 0.")

        try:
            get_args: dict[str, Any] = {
                "include": ["documents", "metadatas", "embeddings"],
            }
            if limit is not None:
                get_args["limit"] = limit
            # allow optional metadata filtering
            # callers may pass a `where` dict to restrict returned chunks
            if where is not None:
                get_args["where"] = where

            results = self.collection.get(**get_args)
        except Exception as exc:
            raise VectorDBOperationError("Failed to read chunks from ChromaDB collection.") from exc

        ids = results.get("ids", []) or []
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        embeddings = results.get("embeddings")
        try:
            embedding_count = len(embeddings) if embeddings is not None else 0
        except TypeError:
            embedding_count = 0

        logger.info(
            "Chroma collection.get diagnostics: collection=%s document_count=%s metadata_count=%s embedding_count=%s ids=%s",
            self.collection_name,
            len(documents),
            len(metadatas),
            embedding_count,
            ids,
        )

        formatted = self._format_get_results(results)
        logger.info(
            "Chroma get completed: collection=%s limit=%s results=%s",
            self.collection_name,
            limit,
            len(formatted),
        )
        return formatted

    def backfill_missing_access_level(self, default_access_level: str = "public") -> int:
        """Add default access metadata to legacy Chroma records when possible.

        Older ingests did not persist ``access_level`` even though retrieval now
        filters by it. Updating metadata in place avoids requiring users to
        delete and reingest existing vectors.
        """

        clean_access_level = str(default_access_level).strip() or "public"

        try:
            results = self.collection.get(include=["metadatas"])
        except Exception as exc:
            raise VectorDBOperationError("Failed to inspect ChromaDB metadata.") from exc

        ids = results.get("ids", []) or []
        metadatas = results.get("metadatas", []) or []

        update_ids: list[str] = []
        update_metadatas: list[dict[str, str | int | float | bool]] = []

        for index, record_id in enumerate(ids):
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            access_level = str(metadata.get("access_level", "")).strip()
            if access_level:
                continue

            metadata["access_level"] = clean_access_level
            update_ids.append(record_id)
            update_metadatas.append(metadata)

        if not update_ids:
            return 0

        try:
            self.collection.update(ids=update_ids, metadatas=update_metadatas)
        except Exception as exc:
            raise VectorDBOperationError(
                "Existing vectors are missing access_level metadata and ChromaDB "
                "could not update them in place. Re-ingestion is required to make "
                "role-filtered retrieval return these legacy chunks."
            ) from exc

        logger.info(
            "Backfilled Chroma access metadata: collection=%s records=%s default_access_level=%s",
            self.collection_name,
            len(update_ids),
            clean_access_level,
        )
        return len(update_ids)

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks for one source document from ChromaDB.

        Args:
            document_id: Stable document ID stored in each chunk metadata.

        Raises:
            VectorDBValidationError: If document_id is empty.
            VectorDBOperationError: If ChromaDB cannot delete the document chunks.
        """

        clean_document_id = document_id.strip()
        if not clean_document_id:
            raise VectorDBValidationError("document_id is required.")

        try:
            # Metadata filtering deletes every chunk that belongs to the document.
            self.collection.delete(where={"document_id": clean_document_id})
        except Exception as exc:
            raise VectorDBOperationError(f"Failed to delete document '{clean_document_id}'.") from exc

    def count_documents(self) -> int:
        """Count stored vector records in the industrial knowledge collection.

        Returns:
            Number of chunk records currently stored in ChromaDB.

        Raises:
            VectorDBOperationError: If ChromaDB cannot count records.
        """

        try:
            # Chroma count returns stored records; in this pipeline, records are chunks.
            return int(self.collection.count())
        except Exception as exc:
            raise VectorDBOperationError("Failed to count ChromaDB records.") from exc

    def reset_collection(self) -> None:
        """Delete and recreate the industrial knowledge collection.

        Raises:
            VectorDBOperationError: If ChromaDB cannot reset the collection.
        """

        try:
            # Dropping only this collection avoids resetting unrelated Chroma databases.
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            # If the collection does not exist, recreating it below is enough.
            pass

        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "INDUS MIND industrial knowledge chunks"},
                embedding_function=None,
            )
        except Exception as exc:
            raise VectorDBOperationError("Failed to reset ChromaDB collection.") from exc

    @staticmethod
    def _validate_chunks_and_embeddings(
        chunks: list[StoredChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Validate stored chunks before sending them to ChromaDB."""

        if not chunks:
            raise VectorDBValidationError("At least one chunk is required.")
        if not embeddings:
            raise VectorDBValidationError("At least one embedding is required.")
        if len(chunks) != len(embeddings):
            raise VectorDBValidationError("chunks and embeddings must have the same length.")

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
            if not chunk.get("chunk_id"):
                raise VectorDBValidationError(f"Chunk {index} is missing chunk_id.")
            if not chunk.get("text"):
                raise VectorDBValidationError(f"Chunk {index} is missing text.")
            if not isinstance(chunk.get("metadata"), dict):
                raise VectorDBValidationError(f"Chunk {index} metadata must be a dictionary.")

            VectorDBService._validate_embedding(embedding, field_name=f"embedding {index}")

    @staticmethod
    def _validate_embedding(embedding: list[float], *, field_name: str) -> None:
        """Ensure an embedding is a non-empty list of numbers."""

        if not embedding:
            raise VectorDBValidationError(f"{field_name} cannot be empty.")
        if not all(isinstance(value, int | float) for value in embedding):
            raise VectorDBValidationError(f"{field_name} must contain only numbers.")

    @staticmethod
    def _build_metadata(chunk: StoredChunk) -> dict[str, str | int | float | bool]:
        """Build Chroma-safe metadata for one chunk."""

        source_metadata = chunk["metadata"]

        # Chroma metadata values must be simple scalar values.
        metadata: dict[str, str | int | float | bool] = {
            "chunk_id": chunk["chunk_id"],
            "document_id": str(source_metadata.get("document_id", "")),
            "filename": str(source_metadata.get("filename", "")),
            "access_level": str(source_metadata.get("access_level", "public")).strip() or "public",
            "page_start": VectorDBService._metadata_int(chunk.get("page_start")),
            "page_end": VectorDBService._metadata_int(chunk.get("page_end")),
            "chunk_index": VectorDBService._metadata_int(source_metadata.get("chunk_index")),
        }

        missing_fields = [key for key, value in metadata.items() if value == "" or value == -1]
        if missing_fields:
            raise VectorDBValidationError(
                f"Chunk '{chunk['chunk_id']}' is missing metadata fields: {', '.join(missing_fields)}."
            )

        optional_fields = (
            "heading",
            "title",
            "problem_statement_number",
            "section_number",
            "chapter_number",
            "figure_number",
            "table_number",
        )
        for field in optional_fields:
            value = VectorDBService._metadata_scalar(source_metadata.get(field))
            if value is not None:
                metadata[field] = value

        return metadata

    @staticmethod
    def _metadata_int(value: Any) -> int:
        """Convert metadata page/index values into Chroma-safe integers."""

        if value is None:
            return -1
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    @staticmethod
    def _metadata_scalar(value: Any) -> str | int | float | bool | None:
        """Return a Chroma-safe scalar metadata value when one is available."""

        if value is None:
            return None
        if isinstance(value, bool | int | float):
            return value

        clean_value = str(value).strip()
        if not clean_value:
            return None

        return clean_value[:500]

    @staticmethod
    def _format_search_results(results: dict[str, Any]) -> list[VectorSearchResult]:
        """Convert Chroma's batch query response into a simple list."""

        ids = results.get("ids", [[]])[0] or []
        documents = results.get("documents", [[]])[0] or []
        metadatas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []

        formatted_results: list[VectorSearchResult] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            formatted_results.append(
                {
                    "chunk_id": chunk_id,
                    "text": documents[index] if index < len(documents) else "",
                    "distance": distances[index] if index < len(distances) else None,
                    "metadata": metadata,
                }
            )

        return formatted_results

    @staticmethod
    def _format_get_results(results: dict[str, Any]) -> list[VectorSearchResult]:
        """Convert Chroma's get response into vector-search-shaped records."""

        ids = results.get("ids", []) or []
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        formatted_results: list[VectorSearchResult] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            formatted_results.append(
                {
                    "chunk_id": chunk_id,
                    "text": documents[index] if index < len(documents) else "",
                    "distance": None,
                    "metadata": metadata,
                }
            )

        return formatted_results

        docs = self.collection.get(include=["metadatas"])

        for meta in docs["metadatas"]:
            print(meta.get("document_id"))
