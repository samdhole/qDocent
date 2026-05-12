# pattern: Imperative Shell
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.services import r2r_client
from apps.api.routes.notebooks import resolve_collection_id

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    notebook_id: str | None = None


@router.post("/ask")
def ask(body: AskRequest) -> dict:
    collection_id = resolve_collection_id(body.notebook_id)

    try:
        return r2r_client.rag_query(body.question, collection_id=collection_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
