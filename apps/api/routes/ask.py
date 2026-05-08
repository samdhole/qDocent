from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.services import r2r_client

router = APIRouter()


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(body: AskRequest) -> dict:
    try:
        return r2r_client.rag_query(body.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
