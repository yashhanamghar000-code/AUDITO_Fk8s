import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance, FieldCondition, Filter, MatchAny, MatchValue,
    PayloadSchemaType, PointStruct, SearchParams, VectorParams,
)

from add_ai_core.entities.document import DocumentChunk
from add_ai_core.interfaces.vector_store import IVectorStore


class QdrantVectorStore(IVectorStore):
    

    def __init__(self, url: str, api_key: Optional[str], collection_name: str, embedding_dim: int, batch_size: int = 100):
        self._collection_name = collection_name
        self._batch_size = batch_size
        self._client = QdrantClient(url=url, api_key=api_key, timeout=60.0)
        self._ensure_collection(embedding_dim)

    def _ensure_collection(self, embedding_dim: int) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection_name not in existing:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
            )
        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        
        for field_name in ("user_id", "session_id", "file_id"):
            try:
                self._client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name=field_name,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except UnexpectedResponse:
                pass  # index already exists
            except Exception as e:
                print(f"[Qdrant] Warning: could not ensure index on '{field_name}': {e}")

    def upsert(
        self,
        chunks: List[DocumentChunk],
        vectors: List[List[float]],
        user_id: str,
        session_id: str,
    ) -> None:

        if len(chunks) != len(vectors):
            raise ValueError(
                f"Chunks/vectors mismatch: chunks={len(chunks)}, vectors={len(vectors)}"
            )

        points = []

        for chunk, vector in zip(chunks, vectors):

            if len(vector) != 384:
                raise ValueError(
                    f"Invalid embedding dimension: expected 384, got {len(vector)}"
                )

            payload = {
                "text": chunk.content,
                "user_id": user_id,
                "session_id": session_id,
                **chunk.metadata,
            }

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )

        print(
            f"[Qdrant] Preparing {len(points)} points "
            f"for collection '{self._collection_name}'"
        )

        batch_size = 25

        total_batches = (len(points) + batch_size - 1) // batch_size

        for i in range(0, len(points), batch_size):

            batch = points[i:i + batch_size]
            batch_number = i // batch_size + 1
            last_error = None

            print(
                f"[Qdrant] Upserting batch "
                f"{batch_number}/{total_batches} "
                f"({len(batch)} points)"
            )

            for attempt in range(1, 4):

                try:

                    self._client.upsert(
                        collection_name=self._collection_name,
                        points=batch,
                        wait=True,
                    )

                    print(
                        f"[Qdrant] Batch {batch_number} "
                        f"successfully upserted"
                    )

                    last_error = None
                    break

                except Exception as e:

                    last_error = e

                    print(
                        f"[Qdrant] Batch {batch_number} "
                        f"failed on attempt {attempt}/3: {e}"
                    )

                    if attempt < 3:
                        import time
                        time.sleep(2 * attempt)

            if last_error is not None:
                raise last_error

    def search(self, query_vector: List[float], user_id: str, top_k: int, file_ids: Optional[List[str]] = None) -> List[DocumentChunk]:

        if not file_ids:
            return[]     

        must = [FieldCondition(
            key="user_id", 
            match=MatchValue(value=user_id)
            )
        ]
        must.append(
            FieldCondition(
                key="file_id",
                match=MatchAny(any=[str(f) for f in file_ids])
            )
        )

        qfilter = Filter(must=must)
        
        search_params = SearchParams(exact=True) 

        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=qfilter,
            limit=top_k,
            search_params=search_params,
        )
        return [
            DocumentChunk(content=hit.payload.get("text", ""), metadata=hit.payload)
            for hit in response.points
        ]

    def delete_session(self, user_id: str, session_id: str) -> None:
        """Wipes only this user+session's vectors, not the whole collection."""
        qfilter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="session_id", match=MatchValue(value=session_id)),
        ])
        
        self._client.delete(collection_name=self._collection_name, points_selector=qfilter, wait=True)

    def delete_file(self, user_id: str, file_id: str) -> None:
        """Wipes only the vectors belonging to ONE uploaded file, leaving
        that user's other files in this session/chat intact."""
        qfilter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="file_id", match=MatchValue(value=file_id)),
        ])
        self._client.delete(collection_name=self._collection_name, points_selector=qfilter, wait=True)
