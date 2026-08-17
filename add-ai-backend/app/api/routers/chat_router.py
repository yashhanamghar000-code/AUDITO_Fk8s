import traceback
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Form, HTTPException

from app.api.dependencies import get_container, get_current_user
from app.container import Container

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def secure_chat(
    query: str = Form(...),
    session_id: str = Form(...),
    file_ids: str = Form(None),
    container: Container = Depends(get_container),
    current_user: SimpleNamespace = Depends(get_current_user),
):
    user_id = str(current_user.id)
    try:
        # Never trust the client's file_ids as the sole source of truth for
        # what this answer is allowed to see. Resolve the files that are
        # ACTUALLY still indexed for this user's session from the database.
        # This is what makes a deleted file's data stop being searchable
        # the moment it's deleted, and stops a stale/leftover client-side
        # file list (e.g. from another conversation) from ever widening
        # the search beyond this session's own documents.
        session_files = container.history_service.list_files_for_conversation(current_user.id, session_id)
        indexed_file_ids = {f["id"] for f in session_files if f["status"] == "indexed"}

        if not indexed_file_ids:
            raise HTTPException(
                status_code=404,
                detail="No documents are available in this conversation. Upload a document before asking a question.",
            )

        requested_file_ids = [f.strip() for f in file_ids.split(",") if f.strip()] if file_ids else []
        if requested_file_ids:
            # Client wants to scope to specific files — honor only the ones
            # that actually still exist (and belong to this session); drop
            # anything stale (e.g. a file id from a document that has since
            # been deleted).
            selected_file_ids = [f for f in requested_file_ids if f in indexed_file_ids]
            if not selected_file_ids:
                raise HTTPException(
                    status_code=404,
                    detail="The selected document(s) are no longer available. Please refresh and try again.",
                )
        else:
            # No explicit selection from the client — default to every
            # currently-indexed file IN THIS SESSION ONLY, never the user's
            # entire upload history across other conversations.
            selected_file_ids = list(indexed_file_ids)

        answer = container.chat_workflow_service.run(
            query=query,
            user_id=user_id,
            session_id=session_id,
            selected_file_ids=selected_file_ids,
        )

        container.history_service.save_chat_turn(current_user.id, session_id, query, answer.response_text)
        return answer.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM Orchestration Error: {str(e)}")
