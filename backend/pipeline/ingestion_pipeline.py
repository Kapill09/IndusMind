import logging
from pathlib import Path
from time import perf_counter
from typing import Protocol, TypedDict, cast

from backend.services.chunking_service import ChunkingError, TextChunk, chunk_pages
from backend.services.embedding_service import EmbeddingService, EmbeddingServiceError
from backend.services.pdf_service import PDFPageText, PDFParsingError
from backend.services.vectordb_service import (
    COLLECTION_NAME,
    StoredChunk,
    VectorDBService,
    VectorDBServiceError,
)
from backend.services.bm25_service import BM25Service
from backend.services.entity_extractor import EntityExtractor


logger = logging.getLogger(__name__)


class PDFService(Protocol):
    """Minimum PDF service contract required by the ingestion pipeline."""

    def extract_text_from_pdf(self, pdf_path: str | Path) -> list[PDFPageText]:
        """Extract page-wise text from a PDF file."""


class IngestionSummary(TypedDict):
    """Structured result returned after a document is ingested."""

    filename: str
    pages: int
    chunks: int
    vectors: int
    collection: str
    success: bool


class IngestionPipelineError(Exception):
    """Base exception for ingestion pipeline failures."""


class IngestionValidationError(IngestionPipelineError):
    """Raised when the input document cannot be ingested."""


class IngestionExtractionError(IngestionPipelineError):
    """Raised when the PDF text extraction step fails."""


class IngestionChunkingError(IngestionPipelineError):
    """Raised when extracted text cannot be chunked."""


class IngestionEmbeddingError(IngestionPipelineError):
    """Raised when chunk embeddings cannot be generated."""


class IngestionStorageError(IngestionPipelineError):
    """Raised when chunks and embeddings cannot be stored."""


class IngestionPipeline:
    """Orchestrate PDF ingestion for the INDUS MIND RAG system.

    The pipeline coordinates existing services. It intentionally avoids parsing
    PDFs, splitting text, generating embeddings inside ChromaDB, or writing
    vector database logic here.
    """

    def __init__(
        self,
        pdf_service: PDFService,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        bm25_service: BM25Service | None = None,
        entity_extractor: EntityExtractor | None = None,
    ) -> None:
        # Services are injected so the pipeline is easy to test and replace.
        self.pdf_service = pdf_service
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.bm25_service = bm25_service or BM25Service()
        self.entity_extractor = entity_extractor or EntityExtractor()

    def ingest_document(self, pdf_path: str | Path, access_level: str = "public") -> IngestionSummary:
        """Ingest one PDF into the industrial knowledge ChromaDB collection."""

        path = self._validate_pdf_path(pdf_path)
        document_id = path.stem
        pipeline_started_at = perf_counter()

        logger.info("Starting ingestion: filename=%s document_id=%s", path.name, document_id)

        try:
            # Step 1: Extract page text so downstream stages work with plain text.
            started_at = perf_counter()
            pages = self.pdf_service.extract_text_from_pdf(path)
            logger.info(
                "PDF extracted: filename=%s pages=%s latency_ms=%s",
                path.name,
                len(pages),
                int((perf_counter() - started_at) * 1000),
            )
        except (FileNotFoundError, PDFParsingError) as exc:
            raise IngestionExtractionError(f"Failed to extract text from '{path.name}'.") from exc

        if not pages:
            raise IngestionValidationError(f"PDF '{path.name}' did not contain any pages.")

        try:
            # Step 2: Chunk pages so retrieval can find focused, relevant passages.
            started_at = perf_counter()
            chunks = chunk_pages(
                pages,
                document_id=document_id,
                metadata={"filename": path.name, "access_level": access_level},
            )
            logger.info(
                "Chunking completed: filename=%s chunks=%s latency_ms=%s",
                path.name,
                len(chunks),
                int((perf_counter() - started_at) * 1000),
            )
        except ChunkingError as exc:
            raise IngestionChunkingError(f"Failed to chunk '{path.name}'.") from exc

        if not chunks:
            raise IngestionValidationError(f"PDF '{path.name}' did not contain extractable text.")

        try:
            # Step 3: Generate embeddings for chunks before storage; ChromaDB
            # receives vectors but does not create them in this architecture.
            started_at = perf_counter()
            embeddings = self.embedding_service.generate_embeddings(
                [chunk["text"] for chunk in chunks]
            )
            logger.info(
                "Embeddings generated: filename=%s vectors=%s latency_ms=%s",
                path.name,
                len(embeddings),
                int((perf_counter() - started_at) * 1000),
            )
        except EmbeddingServiceError as exc:
            raise IngestionEmbeddingError(f"Failed to embed chunks from '{path.name}'.") from exc

        stored_chunks = self._to_stored_chunks(chunks)

        try:
            # Step 4: Store chunk text, metadata, and precomputed vectors together.
            started_at = perf_counter()
            vector_count = self.vectordb_service.add_chunks(stored_chunks, embeddings)
            logger.info(
                "Vectors stored: filename=%s vectors=%s latency_ms=%s",
                path.name,
                vector_count,
                int((perf_counter() - started_at) * 1000),
            )
        except VectorDBServiceError as exc:
            raise IngestionStorageError(f"Failed to store vectors for '{path.name}'.") from exc

        # Step 4.5: Update BM25 index
        try:
            started_at = perf_counter()
            self.bm25_service.add_document([
                {
                    "chunk_id": c["chunk_id"],
                    "text": c["text"],
                    "metadata": c["metadata"]
                } for c in stored_chunks
            ])
            logger.info(
                "BM25 index updated: filename=%s chunks=%s latency_ms=%s",
                path.name,
                len(stored_chunks),
                int((perf_counter() - started_at) * 1000),
            )
        except Exception:
            logger.exception("Failed to update BM25 index for %s", path.name)

        # Step 4.75: Update Entity Registry
        try:
            started_at = perf_counter()
            new_entities = self.entity_extractor.build_registry(
                document_id=document_id,
                chunks=[
                    {
                        "text": c["text"],
                        "metadata": c["metadata"]
                    } for c in stored_chunks
                ]
            )
            logger.info(
                "Entity registry updated: filename=%s new_entities=%d latency_ms=%s",
                path.name,
                new_entities,
                int((perf_counter() - started_at) * 1000),
            )
        except Exception:
            logger.exception("Failed to update entity registry for %s", path.name)

        logger.info(
            "Ingestion completed: filename=%s pages=%s chunks=%s vectors=%s total_latency_ms=%s",
            path.name,
            len(pages),
            len(chunks),
            vector_count,
            int((perf_counter() - pipeline_started_at) * 1000),
        )

        # Step 5: Return counts that callers can log, display, or assert in tests.
        return {
            "filename": path.name,
            "pages": len(pages),
            "chunks": len(chunks),
            "vectors": vector_count,
            "collection": getattr(self.vectordb_service, "collection_name", COLLECTION_NAME),
            "success": True,
        }

    @staticmethod
    def _validate_pdf_path(pdf_path: str | Path) -> Path:
        """Normalize and validate the requested PDF path before ingestion starts."""

        path = Path(pdf_path)
        if not path.exists():
            raise IngestionValidationError(f"PDF file not found: {path}")
        if not path.is_file():
            raise IngestionValidationError(f"PDF path is not a file: {path}")
        if path.suffix.lower() != ".pdf":
            raise IngestionValidationError(f"Expected a .pdf file, got: {path.name}")

        return path

    @staticmethod
    def _to_stored_chunks(chunks: list[TextChunk]) -> list[StoredChunk]:
        """Keep only the fields ChromaDB storage expects."""

        return [
            cast(
                StoredChunk,
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_end"],
                    "metadata": chunk["metadata"],
                },
            )
            for chunk in chunks
        ]
