import pytest

from backend.services.context_constructor import ContextConstructor
from backend.services.prompt_builder import PromptBuilder
from backend.services.query_expander import QueryExpander
from backend.services.query_understanding import QueryIntent, QueryPlan, RetrievalStrategy
from backend.services.response_validator import ResponseValidator
from backend.services.document_selector import DocumentSelection, DocumentScope


class DummyClient:
    class Models:
        @staticmethod
        def generate_content(*args, **kwargs):
            return type("Resp", (), {"text": ""})()

    models = Models()


class DummyVectorDB:
    def get_chunks(self, limit=10, where=None):
        return []


def make_query_plan(intent=QueryIntent.DEFINITION):
    return QueryPlan(
        original_query="What is D2DAP?",
        intent=intent,
        confidence=0.9,
        entities=[],
        documents_referenced=[],
        search_queries=[],
        retrieval_strategy=RetrievalStrategy.SINGLE,
        output_format="standard",
        document_selection=DocumentSelection(
            scope=DocumentScope.ENTIRE_KB,
            selected_ids=[],
            is_scoped=False,
            is_strict=False,
        ),
        num_retrievals=5,
        is_multi_document=False,
        requires_comparison=False,
        requires_table=False,
    )


def test_query_expander_handles_problem_statement_variants():
    expander = QueryExpander(client=DummyClient(), kg_service=None)

    queries = expander.expand("Problem Statement 8", "structural_lookup", [], "multi_query")
    texts = [q.text for q in queries]

    assert any("Problem Statement Eight" in text for text in texts)
    assert any("PS8" in text for text in texts)
    assert any("Challenge 8" in text for text in texts)


def test_context_constructor_formats_and_deduplicates_chunks():
    constructor = ContextConstructor(vectordb_service=DummyVectorDB())
    chunks = [
        {
            "chunk_id": "chunk-001",
            "text": "The pump requires lubrication every 30 days.",
            "score": 0.95,
            "metadata": {
                "document_id": "doc-1",
                "filename": "manual.pdf",
                "chunk_index": 1,
                "page_start": 10,
                "page_end": 10,
            },
        },
        {
            "chunk_id": "chunk-002",
            "text": "The pump requires lubrication every 30 days.",
            "score": 0.94,
            "metadata": {
                "document_id": "doc-1",
                "filename": "manual.pdf",
                "chunk_index": 2,
                "page_start": 11,
                "page_end": 11,
            },
        },
        {
            "chunk_id": "chunk-003",
            "text": "Maintenance should be performed with PPE.",
            "score": 0.9,
            "metadata": {
                "document_id": "doc-1",
                "filename": "manual.pdf",
                "chunk_index": 3,
                "page_start": 12,
                "page_end": 12,
            },
        },
    ]

    formatted = constructor.construct(chunks, make_query_plan(), max_tokens=1000)

    assert formatted
    assert any("Document:" in chunk["text"] for chunk in formatted)
    assert any("Section:" in chunk["text"] for chunk in formatted)
    assert any("Page:" in chunk["text"] for chunk in formatted)
    assert any("Source:" in chunk["text"] for chunk in formatted)
    assert len(formatted) <= 2


def test_prompt_builder_uses_comparison_table_structure():
    prompt = PromptBuilder().build(
        "Compare D2DAP and TLS",
        "context",
        "comparison",
        "comparison",
    )

    assert "Comparison Table" in prompt
    assert "Pros" in prompt
    assert "Recommendation" in prompt
    assert "Never output raw context" in prompt


def test_response_validator_rejects_context_echo_and_short_definition():
    validator = ResponseValidator(client=DummyClient())
    answer = "Based on the retrieved context. === Document === chunk-0001 [source: abc]"

    result = validator.validate(answer, make_query_plan(QueryIntent.DEFINITION), [{"text": "ctx"}])

    assert result.is_valid is False
    assert "context" in result.reason.lower() or "chunk" in result.reason.lower()

    short_answer = "This is a brief definition with limited detail."
    result_two = validator.validate(short_answer, make_query_plan(QueryIntent.DEFINITION), [{"text": "ctx"}])

    assert result_two.is_valid is False
    assert "80" in result_two.reason or "word" in result_two.reason.lower()
