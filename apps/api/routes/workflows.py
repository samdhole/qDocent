from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.workflows.support_triage_graph import run_support_triage
from packages.workflows.email_draft_graph import run_email_draft

router = APIRouter(prefix="/workflows")


class WorkflowRequest(BaseModel):
    message: str


@router.post("/support/triage")
def support_triage(body: WorkflowRequest) -> dict:
    try:
        return run_support_triage(body.message)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/support/email-draft")
def email_draft(body: WorkflowRequest) -> dict:
    try:
        return run_email_draft(body.message)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
