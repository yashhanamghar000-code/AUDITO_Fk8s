from unittest.mock import MagicMock

from app.ingestion_orchestrator import IngestionOrchestrator


def test_ingest_happy_path():
    parsing = MagicMock()
    parsing.parse.return_value = [{"content": "hello", "metadata": {}}]
    embeddings = MagicMock()
    embeddings.embed_documents.return_value = [[0.1, 0.2]]
    vector_store = MagicMock()
    sparse_index = MagicMock()

    orchestrator = IngestionOrchestrator(parsing, embeddings, vector_store, sparse_index)
    count = orchestrator.ingest("f.pdf", "f.pdf", "u1", "s1", "1")

    assert count == 1
    vector_store.upsert.assert_called_once()
    sparse_index.add_documents.assert_called_once()
