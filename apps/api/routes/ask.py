# pattern: Imperative Shell
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.services import notebook_store, r2r_client

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    notebook_id: str | None = None


@router.post("/ask")
def ask(body: AskRequest) -> dict:
    collection_id: str | None = None
    if body.notebook_id:
        nb = notebook_store.get_notebook(body.notebook_id)
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook not found")
        collection_id = nb.get("r2r_collection_id") or None

    try:
        return r2r_client.rag_query(body.question, collection_id=collection_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
