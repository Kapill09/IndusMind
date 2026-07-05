from dataclasses import dataclass
import re
from typing import Any, TypedDict


class TextChunk(TypedDict):
    """A single chunk ready for embedding and vector database storage."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    char_start: int
    char_end: int
    token_estimate: int
    metadata: dict[str, Any]


class PageText(TypedDict):
    """Input shape for text extracted from a PDF page."""

    page: int
    text: str


@dataclass(frozen=True)
class ChunkingConfig:
    """Settings that control how text is split for retrieval."""

    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_size: int = 120
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", "; ", ", ", " ")


class ChunkingError(ValueError):
    """Raised when chunking settings or input text are invalid."""


def chunk_text(
    text: str,
    *,
    document_id: str = "document",
    config: ChunkingConfig | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    """Split plain text into overlapping chunks for a RAG pipeline.

    Args:
        text: Full document text to split.
        document_id: Stable ID used to build deterministic chunk IDs.
        config: Optional chunking settings.
        metadata: Extra metadata copied onto every chunk.

    Returns:
        A list of structured chunks with text, offsets, token estimate, and metadata.

    Raises:
        ChunkingError: If the config is invalid.
    """

    active_config = config or ChunkingConfig()
    _validate_config(active_config)

    # Normalize whitespace so embeddings are not polluted by repeated spaces.
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    base_metadata = metadata or {}
    chunk_ranges = _build_chunk_ranges(normalized_text, active_config)

    chunks: list[TextChunk] = []
    for index, (start, end) in enumerate(chunk_ranges, start=1):
        chunk_body = normalized_text[start:end].strip()
        if not chunk_body:
            continue

        chunks.append(
            {
                "chunk_id": f"{document_id}:chunk-{index:04d}",
                "text": chunk_body,
                "page_start": None,
                "page_end": None,
                "char_start": start,
                "char_end": end,
                "token_estimate": _estimate_tokens(chunk_body),
                "metadata": {
                    **base_metadata,
                    "document_id": document_id,
                    "chunk_index": index,
                },
            }
        )

    return chunks


def chunk_pages(
    pages: list[PageText],
    *,
    document_id: str = "document",
    config: ChunkingConfig | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    """Split page-wise PDF text into chunks while preserving page metadata.

    Args:
        pages: Page text dictionaries, usually returned by the PDF parsing service.
        document_id: Stable ID used to build deterministic chunk IDs.
        config: Optional chunking settings.
        metadata: Extra metadata copied onto every chunk.

    Returns:
        A list of chunks with page ranges and character offsets.
    """

    # Join pages with clear boundaries so chunks can cross pages when useful.
    full_text_parts: list[str] = []
    page_ranges: list[tuple[int, int, int]] = []
    cursor = 0

    for page in pages:
        page_number = page["page"]
        page_text = _normalize_text(page.get("text", ""))
        if not page_text:
            continue

        if full_text_parts:
            full_text_parts.append("\n\n")
            cursor += 2

        start = cursor
        full_text_parts.append(page_text)
        cursor += len(page_text)
        page_ranges.append((page_number, start, cursor))

    chunks = chunk_text(
        "".join(full_text_parts),
        document_id=document_id,
        config=config,
        metadata=metadata,
    )

    # Add page_start and page_end after chunking by comparing character offsets.
    for chunk in chunks:
        page_start, page_end = _find_page_range(
            chunk["char_start"],
            chunk["char_end"],
            page_ranges,
        )
        chunk["page_start"] = page_start
        chunk["page_end"] = page_end
        chunk["metadata"] = {
            **chunk["metadata"],
            "page_start": page_start,
            "page_end": page_end,
        }

    return chunks


def _validate_config(config: ChunkingConfig) -> None:
    """Validate chunking settings before processing starts."""

    if config.chunk_size <= 0:
        raise ChunkingError("chunk_size must be greater than 0.")
    if config.chunk_overlap < 0:
        raise ChunkingError("chunk_overlap cannot be negative.")
    if config.chunk_overlap >= config.chunk_size:
        raise ChunkingError("chunk_overlap must be smaller than chunk_size.")
    if config.min_chunk_size < 0:
        raise ChunkingError("min_chunk_size cannot be negative.")


def _normalize_text(text: str) -> str:
    """Clean repeated whitespace while preserving paragraph breaks."""

    # Convert Windows and old Mac line endings to standard newlines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove repeated spaces and tabs, but leave newlines intact.
    text = re.sub(r"[ \t]+", " ", text)

    # Keep paragraph boundaries readable without allowing huge blank areas.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _build_chunk_ranges(text: str, config: ChunkingConfig) -> list[tuple[int, int]]:
    """Create start and end offsets for each chunk."""

    ranges: list[tuple[int, int]] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        target_end = min(start + config.chunk_size, text_length)
        end = _choose_split_point(text, start, target_end, config)

        # Avoid tiny final chunks by merging them into the previous chunk.
        if ranges and text_length - end < config.min_chunk_size:
            ranges[-1] = (ranges[-1][0], text_length)
            break

        ranges.append((start, end))

        if end == text_length:
            break

        # Overlap gives retrievers context that may span chunk boundaries.
        start = _choose_overlap_start(text, start, end, config.chunk_overlap)

    return ranges


def _choose_split_point(
    text: str,
    start: int,
    target_end: int,
    config: ChunkingConfig,
) -> int:
    """Prefer natural breakpoints such as paragraphs and sentences."""

    if target_end >= len(text):
        return len(text)

    search_window = text[start:target_end]
    minimum_end = min(len(search_window), config.min_chunk_size)

    for separator in config.separators:
        split_at = search_window.rfind(separator)
        if split_at >= minimum_end:
            return start + split_at + len(separator)

    return target_end


def _choose_overlap_start(text: str, previous_start: int, previous_end: int, overlap: int) -> int:
    """Choose the next chunk start without cutting through a word."""

    raw_start = max(previous_end - overlap, previous_start + 1)
    if raw_start >= len(text) or text[raw_start].isspace():
        return raw_start

    # Move forward to the next whitespace so chunks begin cleanly.
    next_space = text.find(" ", raw_start, previous_end)
    next_newline = text.find("\n", raw_start, previous_end)
    candidates = [index for index in (next_space, next_newline) if index != -1]

    if candidates:
        return min(candidates) + 1

    return raw_start


def _find_page_range(
    chunk_start: int,
    chunk_end: int,
    page_ranges: list[tuple[int, int, int]],
) -> tuple[int | None, int | None]:
    """Find the first and last page touched by a chunk."""

    touched_pages = [
        page_number
        for page_number, page_start, page_end in page_ranges
        if chunk_start < page_end and chunk_end > page_start
    ]

    if not touched_pages:
        return None, None

    return min(touched_pages), max(touched_pages)


def _estimate_tokens(text: str) -> int:
    """Estimate token count without requiring a tokenizer dependency."""

    # English technical text is often close to four characters per token.
    return max(1, len(text) // 4)
