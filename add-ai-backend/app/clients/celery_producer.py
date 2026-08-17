from celery import Celery

from app.config.settings import settings


def _normalize_redis_url(raw_url: str) -> str:
    if raw_url.startswith("rediss://") and "ssl_cert_reqs" not in raw_url:
        separator = "&" if "?" in raw_url else "?"
        return f"{raw_url}{separator}ssl_cert_reqs=CERT_NONE"
    return raw_url


_redis_url = _normalize_redis_url(settings.redis_url)

celery_client = Celery("add_ai_backend_producer", broker=_redis_url, backend=_redis_url)


def enqueue_ingestion(file_path: str, file_name: str, user_id: str, session_id: str, file_id: str):
    return celery_client.send_task(
        "app.tasks.process_document_task",
        args=[file_path, file_name, user_id, session_id, file_id],
    )