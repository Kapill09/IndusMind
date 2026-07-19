import unittest

from backend.services.entity_extractor import EntityExtractor
from backend.services.query_understanding import QueryIntent, QueryUnderstandingEngine


class QueryUnderstandingQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = QueryUnderstandingEngine()

    def analyze(self, query: str):
        return self.engine.analyze(query)

    def test_what_is_d2dap_is_definition_not_comparison(self) -> None:
        plan = self.analyze("What is D2DAP?")

        self.assertEqual(plan.intent, QueryIntent.DEFINITION)
        self.assertFalse(plan.requires_comparison)
        self.assertEqual([entity.text for entity in plan.entities], ["D2DAP"])
        self.assertEqual(
            [search_query.text for search_query in plan.search_queries],
            ["What is D2DAP", "D2DAP overview", "D2DAP authentication protocol"],
        )

    def test_who_proposed_d2dap_is_definition(self) -> None:
        plan = self.analyze("Who proposed D2DAP?")

        self.assertEqual(plan.intent, QueryIntent.DEFINITION)
        self.assertFalse(plan.requires_comparison)
        self.assertIn("D2DAP", [entity.text for entity in plan.entities])

    def test_define_bm25_is_definition(self) -> None:
        plan = self.analyze("Define BM25.")

        self.assertEqual(plan.intent, QueryIntent.DEFINITION)
        self.assertFalse(plan.requires_comparison)

    def test_explain_cross_encoder_is_explanation(self) -> None:
        plan = self.analyze("Explain Cross Encoder.")

        self.assertEqual(plan.intent, QueryIntent.EXPLANATION)
        self.assertFalse(plan.requires_comparison)
        self.assertEqual(
            [search_query.text for search_query in plan.search_queries],
            ["Cross Encoder architecture", "Cross Encoder reranking", "Cross Encoder working"],
        )

    def test_summarize_problem_statement_is_summary(self) -> None:
        plan = self.analyze("Summarize Problem Statement 8.")

        self.assertEqual(plan.intent, QueryIntent.SUMMARIZATION)
        self.assertFalse(plan.requires_comparison)
        self.assertEqual(
            [search_query.text for search_query in plan.search_queries],
            ["Problem Statement 8 summary", "Problem Statement 8 overview"],
        )

    def test_compare_bm25_and_dense_retrieval_is_comparison(self) -> None:
        plan = self.analyze("Compare BM25 and Dense Retrieval.")

        self.assertEqual(plan.intent, QueryIntent.COMPARISON)
        self.assertTrue(plan.requires_comparison)
        self.assertIn("BM25 vs Dense Retrieval", [search_query.text for search_query in plan.search_queries])

    def test_difference_between_tls_and_d2dap_is_comparison(self) -> None:
        plan = self.analyze("Difference between TLS and D2DAP.")

        self.assertEqual(plan.intent, QueryIntent.COMPARISON)
        self.assertTrue(plan.requires_comparison)
        self.assertIn("TLS vs D2DAP", [search_query.text for search_query in plan.search_queries])

    def test_open_d2dap_paper_is_navigation(self) -> None:
        plan = self.analyze("Open the D2DAP paper.")

        self.assertEqual(plan.intent, QueryIntent.NAVIGATION)
        self.assertFalse(plan.requires_comparison)

    def test_acronym_definition_edge_cases_are_not_comparisons(self) -> None:
        for query in ("What is IoD?", "What is PUF?", "What is AES?", "What is RSA?"):
            with self.subTest(query=query):
                plan = self.analyze(query)
                self.assertEqual(plan.intent, QueryIntent.DEFINITION)
                self.assertFalse(plan.requires_comparison)

    def test_entity_extractor_does_not_emit_single_letter_or_partial_acronyms(self) -> None:
        extractor = EntityExtractor()
        entities = [entity.text for entity in extractor.extract("What is D2DAP?")]

        self.assertEqual(entities, ["D2DAP"])
        self.assertNotIn("D2D", entities)
        self.assertNotIn("A", entities)


if __name__ == "__main__":
    unittest.main()
