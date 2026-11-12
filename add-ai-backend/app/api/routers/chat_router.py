import traceback

from types import SimpleNamespace

from fastapi import APIRouter, Depends, Form, HTTPException

from app.api.dependencies import get_container, get_current_user
from app.container import Container


router = APIRouter(
    prefix="/api",
    tags=["chat"],
)


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
        # =========================================================
        # DOCUMENT SCOPE
        #
        # Documents belong to the USER, not to the CHAT.
        #
        # session_id:
        #   - identifies the conversation
        #   - controls chat history
        #
        # user_id:
        #   - identifies document ownership
        #   - controls document retrieval
        #
        # file_id:
        #   - optionally restricts retrieval to selected files
        # =========================================================

        user_files = container.history_service.list_files_for_user(
            current_user.id
        )

        # Only indexed files can participate in RAG.
        indexed_file_ids = {
            str(file_record["id"])
            for file_record in user_files
            if str(file_record.get("status", "")).lower() == "indexed"
        }

        # =========================================================
        # Parse file IDs explicitly selected by the frontend.
        #
        # Example:
        #
        #   "10,12,15"
        #
        # becomes:
        #
        #   ["10", "12", "15"]
        # =========================================================

        requested_file_ids = (
            [
                file_id.strip()
                for file_id in file_ids.split(",")
                if file_id.strip()
            ]
            if file_ids
            else []
        )

        # =========================================================
        # CASE 1:
        # User explicitly selected one or more documents.
        #
        # Only allow files that:
        #   1. belong to this user
        #   2. are indexed
        # =========================================================

        if requested_file_ids:

            selected_file_ids = [
                file_id
                for file_id in requested_file_ids
                if file_id in indexed_file_ids
            ]

            if not selected_file_ids:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "The selected document(s) are no longer "
                        "available or are not indexed. "
                        "Please refresh and try again."
                    ),
                )

        # =========================================================
        # CASE 2:
        # No specific document was selected.
        #
        # None means:
        #
        #   Search ALL indexed documents belonging to this user.
        #
        # We intentionally do NOT create a list of file IDs here.
        # The vector store and sparse index will perform user-wide
        # retrieval.
        # =========================================================

        else:

            selected_file_ids = None

            if not indexed_file_ids:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "No indexed documents are available for "
                        "your account. Upload and index a document "
                        "before asking a document-based question."
                    ),
                )

        # =========================================================
        # RUN RAG WORKFLOW
        # =========================================================

        answer = container.chat_workflow_service.run(
            query=query,
            user_id=user_id,
            session_id=session_id,
            selected_file_ids=selected_file_ids,
        )

        # =========================================================
        # SAVE CHAT HISTORY
        #
        # Chat history remains tied to session_id.
        # =========================================================

        container.history_service.save_chat_turn(
            current_user.id,
            session_id,
            query,
            answer.response_text,
        )

        return answer.to_dict()

    except HTTPException:
        raise

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"LLM Orchestration Error: {str(e)}",
        )
