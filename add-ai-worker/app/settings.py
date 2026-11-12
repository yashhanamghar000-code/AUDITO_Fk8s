import os
from dataclasses import dataclass, field


def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    parsing_service_url: str = field(default_factory=lambda: _env("PARSING_SERVICE_URL", "http://parsing-service:8006"))
    embeddings_service_url: str = field(default_factory=lambda: _env("EMBEDDINGS_SERVICE_URL", "http://embeddings-service:8001"))
    vectorstore_service_url: str = field(default_factory=lambda: _env("VECTORSTORE_SERVICE_URL", "http://vectorstore-service:8004"))
    sparseindex_service_url: str = field(default_factory=lambda: _env("SPARSEINDEX_SERVICE_URL", "http://sparseindex-service:8005"))
    data_service_url: str = field(default_factory=lambda: _env("DATA_SERVICE_URL", "http://data-service:8007"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://redis:6379/0"))


settings = Settings()
