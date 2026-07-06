from dataclasses import dataclass
import logging
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


logger = logging.getLogger(__name__)

STRUCTURED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "problem_statement_number",
        re.compile(
            r"\bproblem\s+(?:(?:statement|stmt)\s*)?(?:number|no\.?|#)?\s*([A-Za-z]?\d+[A-Za-z]?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "section_number",
        re.compile(
            r"\b(?:section|sec\.?)\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chapter_number",
        re.compile(
            r"\b(?:chapter|ch\.?)\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "figure_number",
        re.compile(
            r"\b(?:figure|fig\.?)\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "table_number",
        re.compile(
            r"\btable\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
            re.IGNORECASE,
        ),
    ),
)


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
    chunk_ranges = _merge_tiny_heading_ranges(normalized_text, chunk_ranges, active_config)

    chunks: list[TextChunk] = []
    for index, (start, end) in enumerate(chunk_ranges, start=1):
        chunk_body = normalized_text[start:end].strip()
        if not chunk_body:
            continue

        structured_metadata = _extract_structured_metadata(chunk_body)
        chunk_metadata = _merge_metadata(base_metadata, structured_metadata)
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
                    **chunk_metadata,
                    "document_id": document_id,
                    "chunk_index": index,
                },
            }
        )

    logger.info(
        "Chunked document_id=%s chars=%s chunks=%s",
        document_id,
        len(normalized_text),
        len(chunks),
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


def _extract_structured_metadata(text: str) -> dict[str, str]:
    """Extract navigational metadata used for hybrid retrieval."""

    metadata: dict[str, str] = {}

    # Extract the first heading/title in the chunk.
    first_heading = _extract_heading(text)
    if first_heading:
        metadata["heading"] = first_heading
        metadata["title"] = first_heading

    for metadata_key, pattern in STRUCTURED_PATTERNS:
        match = pattern.search(text)
        if match:
            metadata[metadata_key] = match.group(1).strip()

    # Support PDFs formatted like:
    #
    # 8
    # AI for Industrial Knowledge Intelligence
    #
    number_title_match = re.search(
        r"(?:^|\n)\s*(\d{1,2})\s*\n+\s*([^\n]{5,150})",
        text,
        flags=re.IGNORECASE,
    )

    if number_title_match:
        problem_number = number_title_match.group(1).strip()
        possible_title = number_title_match.group(2).strip(" :-\t")

        if (
            possible_title
            and _looks_like_heading(possible_title)
            and "theme" not in possible_title.lower()
            and "criteria" not in possible_title.lower()
            and "weight" not in possible_title.lower()
            and int(problem_number) <= 20
        ):
            metadata["problem_statement_number"] = problem_number
            metadata["heading"] = possible_title
            metadata["title"] = possible_title

    return metadata


def _extract_heading(text: str) -> str | None:
    """Find a likely heading near the start of a chunk."""

    lines = [
        raw_line.strip(" :-\t")
        for raw_line in text.splitlines()[:8]
        if raw_line.strip(" :-\t")
    ]

    for index, line in enumerate(lines):
        if not line or len(line) > 140:
            continue

        # Number + title layouts are common in hackathon/problem PDFs.
        # Prefer the title line over returning the standalone number.
        if re.fullmatch(r"\d{1,3}", line):
            if index + 1 < len(lines):
                next_line = lines[index + 1]
                if len(next_line) <= 140 and _looks_like_heading(next_line):
                    return next_line
            continue

        problem_label = re.fullmatch(
            r"problem\s+(?:(?:statement|stmt)\s*)?(?:number|no\.?|#)?\s*[A-Za-z]?\d+[A-Za-z]?",
            line,
            flags=re.IGNORECASE,
        )
        if problem_label and index + 1 < len(lines):
            next_line = lines[index + 1]
            if len(next_line) <= 140 and _looks_like_heading(next_line):
                return next_line

        if re.search(r"\b(chapter|ch\.|section|sec\.|problem\s+statement|figure|fig\.|table)\b", line, flags=re.IGNORECASE):
            return line
        if _looks_like_heading(line):
            return line

    return None


def _looks_like_heading(line: str) -> bool:
    """Return True for compact title-like lines near the start of a chunk."""

    words = re.findall(r"[A-Za-z][A-Za-z0-9&+/#.-]*", line)
    if not words or len(words) > 14:
        return False

    letters = re.sub(r"[^A-Za-z]", "", line)
    if not letters:
        return False

    if line.isupper():
        return True

    title_case_words = sum(1 for word in words if word[:1].isupper())
    if title_case_words >= max(1, len(words) - 1):
        return True

    # Allow short mixed-case headings such as "eGovernance Assistant" or
    # "AI powered QA" without accepting long body sentences.
    if len(words) <= 8 and title_case_words >= 1:
        return True

    return False


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


def _merge_tiny_heading_ranges(
    text: str,
    ranges: list[tuple[int, int]],
    config: ChunkingConfig,
) -> list[tuple[int, int]]:
    """Attach heading-only chunks to the content that follows."""

    if len(ranges) < 2:
        return ranges

    merged: list[tuple[int, int]] = []
    index = 0
    while index < len(ranges):
        start, end = ranges[index]
        chunk_text = text[start:end].strip()
        if index + 1 < len(ranges) and _is_tiny_heading_chunk(chunk_text, config):
            _next_start, next_end = ranges[index + 1]
            merged.append((start, next_end))
            index += 2
            continue

        merged.append((start, end))
        index += 1

    return merged


def _is_tiny_heading_chunk(text: str, config: ChunkingConfig) -> bool:
    """Return True when a chunk is only a short heading/title."""

    lines = [line.strip(" :-\t") for line in text.splitlines() if line.strip(" :-\t")]
    if not lines:
        return False
    if len(text) > config.min_chunk_size:
        return False
    if len(lines) == 1:
        return _looks_like_heading(lines[0])
    if len(lines) == 2 and re.fullmatch(r"\d{1,3}", lines[0]):
        return _looks_like_heading(lines[1])

    return False


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
        while split_at >= minimum_end:
            candidate_end = start + split_at + len(separator)
            if not _would_split_heading_from_body(text, candidate_end):
                return candidate_end
            split_at = search_window.rfind(separator, 0, split_at)

    return target_end


def _would_split_heading_from_body(text: str, split_index: int) -> bool:
    """Avoid a chunk boundary immediately after a heading line."""

    before = text[:split_index].rstrip()
    after = text[split_index:].lstrip()
    if not before or not after:
        return False

    heading_line = before.rsplit("\n", 1)[-1].strip(" :-\t")
    if not heading_line:
        return False

    next_line = after.splitlines()[0].strip(" :-\t") if after.splitlines() else ""
    return bool(next_line) and _looks_like_heading(heading_line)


def _merge_metadata(
    base_metadata: dict[str, Any],
    structured_metadata: dict[str, str],
) -> dict[str, Any]:
    """Merge metadata without replacing existing strong values."""

    merged = dict(base_metadata)
    for key, value in structured_metadata.items():
        if _has_metadata_value(merged.get(key)):
            continue
        merged[key] = value

    return merged


def _has_metadata_value(value: Any) -> bool:
    """Return True for metadata values that should not be downgraded."""

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


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
