import unittest

from backend.services.vectordb_service import VectorDBService


class VectorDBAccessLevelTests(unittest.TestCase):
    def test_build_metadata_preserves_access_level(self) -> None:
        metadata = VectorDBService._build_metadata(
            {
                "chunk_id": "doc:chunk-0001",
                "text": "Chunk text",
                "page_start": 1,
                "page_end": 1,
                "metadata": {
                    "document_id": "doc",
                    "filename": "doc.pdf",
                    "chunk_index": 1,
                    "access_level": "engineer",
                },
            }
        )

        self.assertEqual(metadata["access_level"], "engineer")

    def test_build_metadata_defaults_access_level_to_public(self) -> None:
        metadata = VectorDBService._build_metadata(
            {
                "chunk_id": "doc:chunk-0001",
                "text": "Chunk text",
                "page_start": 1,
                "page_end": 1,
                "metadata": {
                    "document_id": "doc",
                    "filename": "doc.pdf",
                    "chunk_index": 1,
                },
            }
        )

        self.assertEqual(metadata["access_level"], "public")

    def test_backfill_missing_access_level_updates_legacy_metadata(self) -> None:
        class FakeCollection:
            def __init__(self) -> None:
                self.records = {
                    "a": {"document_id": "doc_a", "filename": "a.pdf"},
                    "b": {"document_id": "doc_b", "filename": "b.pdf", "access_level": "admin"},
                }
                self.updated_ids: list[str] = []

            def get(self, include: list[str]):
                return {
                    "ids": list(self.records.keys()),
                    "metadatas": [dict(value) for value in self.records.values()],
                }

            def update(self, ids: list[str], metadatas: list[dict[str, object]]) -> None:
                self.updated_ids = ids
                for record_id, metadata in zip(ids, metadatas):
                    self.records[record_id] = dict(metadata)

        fake_collection = FakeCollection()
        service = VectorDBService.__new__(VectorDBService)
        service.collection_name = "test_collection"
        service.collection = fake_collection

        updated = service.backfill_missing_access_level()

        self.assertEqual(updated, 1)
        self.assertEqual(fake_collection.updated_ids, ["a"])
        self.assertEqual(fake_collection.records["a"]["access_level"], "public")
        self.assertEqual(fake_collection.records["b"]["access_level"], "admin")


if __name__ == "__main__":
    unittest.main()
