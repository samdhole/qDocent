# pattern: Imperative Shell
"""Conversation endpoints for multi-turn RAG queries."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.services import r2r_agent

router = APIRouter(prefix="/conversations")


class CreateConversationRequest(BaseModel):
    """Request body for POST /conversations."""

    name: str | None = None


class CreateConversationResponse(BaseModel):
    """Response body for POST /conversations."""

    conversation_id: str


class MessageRequest(BaseModel):
    """Request body for POST /conversations/{id}/messages."""

    message: str


@router.post("", response_model=CreateConversationResponse)
def create_conversation(body: CreateConversationRequest) -> CreateConversationResponse:
    """Create a new conversation and return its ID."""
    try:
        conversation_id = r2r_agent.create_conversation(name=body.name)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CreateConversationResponse(conversation_id=conversation_id)


@router.post("/{conversation_id}/messages")
def post_message(conversation_id: str, body: MessageRequest) -> dict:
    """Send a message in a conversation and return the agent response."""
    try:
        return r2r_agent.agent_query(message=body.message, conversation_id=conversation_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
