import os
import traceback

from add_ai_core.exceptions import IngestionError

from app.celery_app import celery_app
from app.clients.data_client import DataServiceClient
from app.clients.embedding_client import EmbeddingServiceClient
from app.clients.parsing_client import ParsingServiceClient
from app.clients.sparseindex_client import SparseIndexServiceClient
from app.clients.vectorstore_client import VectorStoreServiceClient
from app.ingestion_orchestrator import IngestionOrchestrator
from app.settings import settings


_orchestrator = IngestionOrchestrator(
    parsing_client=ParsingServiceClient(settings.parsing_service_url),
    embedding_client=EmbeddingServiceClient(settings.embeddings_service_url),
    vector_store_client=VectorStoreServiceClient(settings.vectorstore_service_url),
    sparse_index_client=SparseIndexServiceClient(settings.sparseindex_service_url),
)
_data_service = DataServiceClient(settings.data_service_url)


@celery_app.task(bind=True, name="app.tasks.process_document_task")
def process_document_task(self, file_path: str, file_name: str, user_id: str, session_id: str, file_id: str):
    try:
        self.update_state(state="PARSING", meta={"stage": "parsing_document"})

        print(f"[Worker] file_path={repr(file_path)}")
        print(f"[Worker] file_name={repr(file_name)}")
        print(f"[Worker] user_id={repr(user_id)}")
        print(f"[Worker] session_id={repr(session_id)}")
        print(f"[Worker] file_id={repr(file_id)}")
        print(f"[Worker] exists={os.path.exists(file_path)}")
        print(f"[Worker] cwd={os.getcwd()}")

        if not os.path.exists(file_path):
            _data_service.update_file_status(int(file_id), "failed")
            return {"status": "failed", "detail": f"File not found on shared storage: {file_path}"}

        self.update_state(state="EMBEDDING", meta={"stage": "embedding_and_indexing"})
        try:
            total_chunks_indexed = _orchestrator.ingest(
                file_path=file_path,
                file_name=file_name,
                user_id=user_id,
                session_id=session_id,
                file_id=file_id,
            )
        except IngestionError as e:
            _data_service.update_file_status(int(file_id), "failed")
            return {"status": "failed", "detail": str(e)}

        _data_service.update_file_status(int(file_id), "indexed", total_chunks_indexed)

        return {
            "status": "success",
            "total_chunks_indexed": total_chunks_indexed,
            "file_name": file_name,
            "file_id": file_id,
        }

    except Exception as e:
        traceback.print_exc()
        try:
            _data_service.update_file_status(int(file_id), "failed")
        except Exception:
            pass
        return {"status": "failed", "detail": str(e)}
