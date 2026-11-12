
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base, engine, get_db
from app.repositories.sqlalchemy_chat_message_repository import SqlAlchemyChatMessageRepository
from app.repositories.sqlalchemy_conversation_repository import SqlAlchemyConversationRepository
from app.repositories.sqlalchemy_file_repository import SqlAlchemyFileRepository
from app.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository

app = FastAPI(title="add-ai-data-service")
Base.metadata.create_all(bind=engine)


def conversation_repo(db: Session = Depends(get_db)) -> SqlAlchemyConversationRepository:
    return SqlAlchemyConversationRepository(db)


def file_repo(db: Session = Depends(get_db)) -> SqlAlchemyFileRepository:
    return SqlAlchemyFileRepository(db, SqlAlchemyConversationRepository(db))


def chat_message_repo(db: Session = Depends(get_db)) -> SqlAlchemyChatMessageRepository:
    return SqlAlchemyChatMessageRepository(db, SqlAlchemyConversationRepository(db))


def user_repo(db: Session = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- users ---
class CreateUserRequest(BaseModel):
    name: str
    email: str
    hashed_password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    hashed_password: str


@app.post("/users", response_model=UserResponse)
def create_user(req: CreateUserRequest, repo: SqlAlchemyUserRepository = Depends(user_repo)):
    u = repo.create(req.name, req.email, req.hashed_password)
    return UserResponse(id=u.id, name=u.name, email=u.email, hashed_password=u.hashed_password)


@app.get("/users/by-email/{email}", response_model=Optional[UserResponse])
def get_user_by_email(email: str, repo: SqlAlchemyUserRepository = Depends(user_repo)):
    u = repo.get_by_email(email)
    if not u:
        return None
    return UserResponse(id=u.id, name=u.name, email=u.email, hashed_password=u.hashed_password)


@app.get("/users/{user_id}", response_model=Optional[UserResponse])
def get_user_by_id(user_id: int, repo: SqlAlchemyUserRepository = Depends(user_repo)):
    u = repo.get_by_id(user_id)
    if not u:
        return None
    return UserResponse(id=u.id, name=u.name, email=u.email, hashed_password=u.hashed_password)


# ------------------------------------------------------------ conversations
class GetOrCreateConversationRequest(BaseModel):
    user_id: int
    session_id: str
    title_hint: str


@app.post("/conversations/get-or-create")
def get_or_create_conversation(req: GetOrCreateConversationRequest, repo: SqlAlchemyConversationRepository = Depends(conversation_repo)):
    try:
        conv = repo.get_or_create(req.user_id, req.session_id, req.title_hint)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"id": conv.id, "session_id": conv.session_id}


@app.get("/conversations", response_model=List[Dict[str, Any]])
def list_conversations(user_id: int, repo: SqlAlchemyConversationRepository = Depends(conversation_repo)):
    return repo.list_for_user(user_id)


@app.delete("/conversations/{session_id}")
def delete_conversation(session_id: str, user_id: int, repo: SqlAlchemyConversationRepository = Depends(conversation_repo)):
    repo.delete(user_id, session_id)
    return {"deleted": session_id}


# -------------------------------------------------------------- chat msgs
class SaveTurnRequest(BaseModel):
    user_id: int
    session_id: str
    query: str
    response: str


@app.post("/chat-messages/turn")
def save_turn(req: SaveTurnRequest, repo: SqlAlchemyChatMessageRepository = Depends(chat_message_repo)):
    repo.save_turn(req.user_id, req.session_id, req.query, req.response)
    return {"saved": True}


@app.get("/chat-messages/history", response_model=List[Dict[str, Any]])
def get_history(user_id: int, session_id: str, repo: SqlAlchemyChatMessageRepository = Depends(chat_message_repo)):
    return repo.get_history(user_id, session_id)


# -------------------------------------------------------------------- files
class CreatePendingFileRequest(BaseModel):
    user_id: int
    session_id: str
    file_name: str
    file_path: str


@app.post("/files/pending")
def create_pending_file(req: CreatePendingFileRequest, repo: SqlAlchemyFileRepository = Depends(file_repo)):
    f = repo.create_pending(req.user_id, req.session_id, req.file_name, req.file_path)
    return {"id": f.id, "file_path": f.file_path}


class UpdateFileStatusRequest(BaseModel):
    status: str
    total_chunks_indexed: int = 0


@app.patch("/files/{file_id}/status")
def update_file_status(file_id: int, req: UpdateFileStatusRequest, repo: SqlAlchemyFileRepository = Depends(file_repo)):
    repo.update_status(file_id, req.status, req.total_chunks_indexed)
    return {"updated": file_id}


@app.get("/files/{file_id}")
def get_owned_file(file_id: int, user_id: int, repo: SqlAlchemyFileRepository = Depends(file_repo)):
    f = repo.get_owned(user_id, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": f.id, "file_name": f.file_name, "status": f.status, "file_path": f.file_path}


@app.delete("/files/{file_id}")
def delete_file(file_id: int, user_id: int, repo: SqlAlchemyFileRepository = Depends(file_repo)):
    info = repo.delete(user_id, file_id)
    if info is None:
        raise HTTPException(status_code=404, detail="not found")
    return info


@app.get("/files", response_model=List[Dict[str, Any]])
def list_files_for_conversation(user_id: int, session_id: str, repo: SqlAlchemyFileRepository = Depends(file_repo)):
    return repo.list_for_conversation(user_id, session_id)
