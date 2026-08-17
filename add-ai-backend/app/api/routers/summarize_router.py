import traceback
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Form, HTTPException

from app.api.dependencies import get_container, get_current_user
from app.container import Container

router = APIRouter(prefix="/api", tags=["summarize"])


@router.post("/summarize")
async def summarize_document(
    file_id: str = Form(...),
    container: Container = Depends(get_container),
    current_user: SimpleNamespace = Depends(get_current_user),
):
    user_id = str(current_user.id)
    try:
        summary = container.summarization_service.summarize(user_id=user_id, file_id=file_id)
        return {"status": "success", "file_id": file_id, "summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Summarization Error: {str(e)}")
