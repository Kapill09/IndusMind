from pathlib import Path
from typing import Any, TypedDict

import chromadb


COLLECTION_NAME = "industrial_knowledge"
DEFAULT_CHROMA_PATH = Path(__file__).resolve().parents[2] / "data" / "chroma"


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

        return len(chunks)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
        """Search ChromaDB using a precomputed query embedding.

        Args:
            query_embedding: Embedding vector for the user query.
            top_k: Maximum number of nearest chunks to return.

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
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorDBOperationError("Failed to search ChromaDB collection.") from exc

        return self._format_search_results(results)

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
            "page_start": VectorDBService._metadata_int(chunk.get("page_start")),
            "page_end": VectorDBService._metadata_int(chunk.get("page_end")),
            "chunk_index": VectorDBService._metadata_int(source_metadata.get("chunk_index")),
        }

        missing_fields = [key for key, value in metadata.items() if value == "" or value == -1]
        if missing_fields:
            raise VectorDBValidationError(
                f"Chunk '{chunk['chunk_id']}' is missing metadata fields: {', '.join(missing_fields)}."
            )

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
