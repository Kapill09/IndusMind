import unittest

from backend.routes.ask import sanitize_document_ids
from backend.services.query_analyzer import StructuredQuery
from backend.services.retrieval_service import RetrievalService


class AskDocumentIdSanitizationTests(unittest.TestCase):
    def test_invalid_and_empty_values_are_treated_as_none(self) -> None:
        self.assertIsNone(sanitize_document_ids(None))
        self.assertIsNone(sanitize_document_ids([]))
        self.assertIsNone(sanitize_document_ids([""]))
        self.assertIsNone(sanitize_document_ids(["string"]))
        self.assertIsNone(sanitize_document_ids(["null"]))
        self.assertIsNone(sanitize_document_ids(["undefined"]))
        self.assertIsNone(sanitize_document_ids(["  ", ""]))

    def test_valid_ids_are_trimmed_and_duplicates_removed(self) -> None:
        self.assertEqual(
            sanitize_document_ids([" maintenance_manual_2024 ", "maintenance_manual_2024", "ops_guide"]),
            ["maintenance_manual_2024", "ops_guide"],
        )
        self.assertEqual(
            sanitize_document_ids(["  Problem Statement 8  ", "  ", "problem_statement_8"]),
            ["Problem Statement 8", "problem_statement_8"],
        )

    def test_structured_problem_statement_returns_only_exact_matches(self) -> None:
        class FakeEmbeddingService:
            def generate_embedding(self, question: str) -> list[float]:
                return [0.0, 0.0, 0.0]

        class FakeVectorDBService:
            def get_chunks(self, limit: int | None = None, where: object | None = None):
                return [
                    {
                        "chunk_id": "p8_1",
                        "text": "Problem Statement 8: description.",
                        "distance": 0.0,
                        "metadata": {
                            "document_id": "doc_a",
                            "filename": "doc_a.pdf",
                            "problem_statement_number": "8",
                        },
                    },
                    {
                        "chunk_id": "p1_1",
                        "text": "Problem Statement 1: different issue.",
                        "distance": 0.0,
                        "metadata": {
                            "document_id": "doc_a",
                            "filename": "doc_a.pdf",
                            "problem_statement_number": "1",
                        },
                    },
                ]

            def search(self, query_embedding: list[float], top_k: int = 5, where: object | None = None):
                return []

        service = RetrievalService(FakeEmbeddingService(), FakeVectorDBService())
        response = service.retrieve(question="Problem Statement 8", top_k=5, document_ids=None)

        self.assertEqual(len(response["results"]), 1)
        self.assertEqual(response["results"][0]["metadata"]["problem_statement_number"], "8")

    def test_structured_page_query_returns_only_matching_page_chunks(self) -> None:
        class FakeEmbeddingService:
            def generate_embedding(self, question: str) -> list[float]:
                return [0.0, 0.0, 0.0]

        class FakeVectorDBService:
            def get_chunks(self, limit: int | None = None, where: object | None = None):
                return [
                    {
                        "chunk_id": "page15_1",
                        "text": "Relevant details on page 15.",
                        "distance": 0.0,
                        "metadata": {
                            "document_id": "doc_b",
                            "filename": "doc_b.pdf",
                            "page_start": 15,
                            "page_end": 15,
                        },
                    },
                    {
                        "chunk_id": "page16_1",
                        "text": "Next page content.",
                        "distance": 0.0,
                        "metadata": {
                            "document_id": "doc_b",
                            "filename": "doc_b.pdf",
                            "page_start": 16,
                            "page_end": 16,
                        },
                    },
                ]

            def search(self, query_embedding: list[float], top_k: int = 5, where: object | None = None):
                return []

        service = RetrievalService(FakeEmbeddingService(), FakeVectorDBService())
        response = service.retrieve(question="Page 15", top_k=5, document_ids=None)

        self.assertEqual(len(response["results"]), 1)
        self.assertEqual(response["results"][0]["metadata"]["page_start"], 15)

    def test_structured_fallback_to_hybrid_when_no_structured_results(self) -> None:
        class FakeEmbeddingService:
            def generate_embedding(self, question: str) -> list[float]:
                return [0.0, 0.0, 0.0]

        class FakeVectorDBService:
            def get_chunks(self, limit: int | None = None, where: object | None = None):
                return [
                    {
                        "chunk_id": "no_match",
                        "text": "A chunk without structured identifier.",
                        "distance": 0.0,
                        "metadata": {
                            "document_id": "doc_c",
                            "filename": "doc_c.pdf",
                        },
                    },
                ]

            def search(self, query_embedding: list[float], top_k: int = 5, where: object | None = None):
                return [
                    {
                        "chunk_id": "hybrid_1",
                        "text": "Fallback hybrid result.",
                        "distance": 0.1,
                        "metadata": {
                            "document_id": "doc_c",
                            "filename": "doc_c.pdf",
                        },
                    },
                ]

        service = RetrievalService(FakeEmbeddingService(), FakeVectorDBService())
        response = service.retrieve(question="Problem Statement 42", top_k=5, document_ids=None)

        self.assertEqual(len(response["results"]), 1)
        self.assertEqual(response["results"][0]["chunk_id"], "hybrid_1")


if __name__ == "__main__":
    unittest.main()
