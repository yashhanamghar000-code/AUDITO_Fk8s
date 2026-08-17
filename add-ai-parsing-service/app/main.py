import os
import shutil
import tempfile
from typing import Any, Dict, List

from add_ai_core.entities.document import DocumentChunk
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.parsing.chunk_audit_logger import ChunkAuditLogger
from app.parsing.docx_parser import DocxDocumentParser
from app.parsing.image_parser import ImageOcrDocumentParser
from app.parsing.parser_factory import ParserFactory, UnsupportedFileTypeError
from app.parsing.pdf_parser import PdfDocumentParser
from app.parsing.recursive_document_chunker import RecursiveDocumentChunker
from app.parsing.text_parser import TextDocumentParser

app = FastAPI(title="add-ai-parsing-service")

_parser_max_workers = int(os.getenv("PARSER_MAX_WORKERS", str(max(2, min(3, (os.cpu_count() or 4) - 2)))))
_factory = ParserFactory([
    PdfDocumentParser(max_workers=_parser_max_workers),
    DocxDocumentParser(),
    TextDocumentParser(),
    ImageOcrDocumentParser(),
])
_chunker = RecursiveDocumentChunker()
_audit_logger = ChunkAuditLogger(os.getenv("DEBUG_LOGS_DIR", "/data/debug_logs"))


class Chunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class ParseResponse(BaseModel):
    chunks: List[Chunk]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse)
def parse(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    file_id: str = Form(...),
):
    
    tenant_metadata = {"user_id": user_id, "session_id": session_id, "file_id": file_id}

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parser = _factory.get_parser(file.filename)
        raw_chunks = parser.parse(tmp_path, file.filename, tenant_metadata)
        final_chunks = _chunker.chunk(raw_chunks)
        _audit_logger.log(final_chunks, file.filename, user_id, session_id)
        return ParseResponse(chunks=[Chunk(content=c.content, metadata=c.metadata) for c in final_chunks])
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=str(e))
    finally:
        os.remove(tmp_path)
