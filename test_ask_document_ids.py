import unittest

from backend.routes.ask import sanitize_document_ids


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


if __name__ == "__main__":
    unittest.main()
