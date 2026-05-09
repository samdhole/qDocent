# pattern: Imperative Shell
"""Conversation endpoints for multi-turn RAG queries."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
    doc_only: bool = False
    document_id: str | None = None


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
        return r2r_agent.agent_query(
            message=body.message,
            conversation_id=conversation_id,
            doc_only=body.doc_only,
            document_id=body.document_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{conversation_id}/messages/stream")
def post_message_stream(conversation_id: str, body: MessageRequest) -> StreamingResponse:
    """Stream agent response events as Server-Sent Events.

    Returns text/event-stream with frames containing status, token, final, or error events.
    """
    generator = r2r_agent.agent_stream(
        message=body.message,
        conversation_id=conversation_id,
        doc_only=body.doc_only,
        document_id=body.document_id,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            # Prevent proxy buffering (matters for nginx, also affects Next.js dev proxy in some setups)
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            # CORS already handled at app level, but be explicit for streaming responses:
            "Connection": "keep-alive",
        },
    )
