from typing import List

from add_ai_core.exceptions import IngestionError

from app.clients.embedding_client import EmbeddingServiceClient
from app.clients.parsing_client import ParsingServiceClient
from app.clients.sparseindex_client import SparseIndexServiceClient
from app.clients.vectorstore_client import VectorStoreServiceClient


class IngestionOrchestrator:

    def __init__(
        self,
        parsing_client: ParsingServiceClient,
        embedding_client: EmbeddingServiceClient,
        vector_store_client: VectorStoreServiceClient,
        sparse_index_client: SparseIndexServiceClient,
    ):
        self._parsing = parsing_client
        self._embeddings = embedding_client
        self._vector_store = vector_store_client
        self._sparse_index = sparse_index_client

    def ingest(self, file_path: str, file_name: str, user_id: str, session_id: str, file_id: str) -> int:
        print(f"\n[Ingestion] User: {user_id} | Session: {session_id} | File: {file_id} | Processing: {file_name}")

        chunks = self._parsing.parse(file_path, file_name, user_id, session_id, file_id)
        if not chunks:
            raise IngestionError("No text could be extracted from the file.")

        texts: List[str] = [c["content"] for c in chunks]
        vectors = self._embeddings.embed_documents(texts)

        self._vector_store.upsert(chunks, vectors, user_id, session_id)
        self._sparse_index.add_documents(user_id, chunks)

        return len(chunks)
