import pytest

from backend.pipeline.rag_pipeline import RAGPipeline


def test_build_sources_creates_metadata_for_each_chunk() -> None:
    chunks = [
        {
            "chunk_id": "chunk-1",
            "text": "Pump maintenance guidance.",
            "page_start": 1,
            "page_end": 2,
            "score": 0.91,
            "metadata": {"document_id": "doc-1", "filename": "manual.pdf"},
        },
        {
            "chunk_id": "chunk-2",
            "text": "Safety procedures.",
            "page_start": None,
            "page_end": None,
            "score": None,
            "metadata": {"document_id": "doc-2"},
        },
    ]

    sources = RAGPipeline._build_sources(chunks)

    assert len(sources) == 2
    assert sources[0]["chunk_id"] == "chunk-1"
    assert sources[0]["text"] == "Pump maintenance guidance."
    assert sources[0]["page_start"] == 1
    assert sources[0]["page_end"] == 2
    assert sources[0]["score"] == 0.91
    assert sources[0]["metadata"]["document_id"] == "doc-1"
    assert sources[1]["page_start"] is None
    assert sources[1]["score"] is None
