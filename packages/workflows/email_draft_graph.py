"""Email draft workflow — retrieves policy, drafts an email, always requires approval.

Proposing to send an email is an external action → requires_human_approval always True.
This is a simplified graph for demo purposes.
"""
# pattern: Imperative Shell
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from r2r import R2RClient

from packages.workflows.state import SupportState

load_dotenv()

_R2R_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
_LLM_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gemini-3-flash-preview")
_SEARCH_SETTINGS: dict[str, Any] = {"limit": 3, "graph_settings": {"enabled": False}}


def retrieve_policy(state: SupportState) -> SupportState:
    log = logging.getLogger(__name__)
    try:
        client = R2RClient(base_url=_R2R_URL)
        response = client.retrieval.rag(
            query=state["customer_message"],
            search_settings=_SEARCH_SETTINGS,
        )
        inner = getattr(response, "results", response)
        agg = getattr(inner, "search_results", None)
        chunks = getattr(agg, "chunk_search_results", None) or [] if agg else []
        contexts = [
            {"text": getattr(r, "text", "")[:300], "score": round(getattr(r, "score", 0.0) or 0.0, 4)}
            for r in chunks
        ]
        citations = [
            {"document": (getattr(r, "metadata", {}) or {}).get("source_file", "unknown")}
            for r in chunks
        ]
    except (httpx.ConnectError, httpx.HTTPStatusError, httpx.TimeoutException) as exc:
        log.warning("R2R retrieval failed: %s", exc, exc_info=True)
        contexts, citations = [], []

    return {**state, "retrieved_contexts": contexts, "citations": citations}


def draft_email(state: SupportState) -> SupportState:
    """Draft a polite email response using LLM. Always sets approval required."""
    context_text = "\n".join(c["text"] for c in state["retrieved_contexts"][:3])
    llm = ChatGoogleGenerativeAI(model=_LLM_MODEL, temperature=0.3)
    prompt = (
        f"You are a helpful support agent. Draft a polite, professional email response "
        f"to this customer message. Use only the policy context provided.\n\n"
        f"Customer message: {state['customer_message']}\n\n"
        f"Policy context:\n{context_text or 'No policy context found.'}\n\n"
        f"Draft email (subject and body):"
    )
    raw = llm.invoke(prompt).content
    draft = (raw[0].get("text", "") if isinstance(raw, list) else raw).strip()
    confidence = "medium" if state["retrieved_contexts"] else "low"
    return {
        **state,
        "draft_response": draft,
        "confidence_label": confidence,
        "requires_human_approval": True,  # Always — email send is an external action
        "final_response": "[Awaiting human approval before sending email]",
    }


def _build_email_graph() -> Any:
    graph = StateGraph(SupportState)
    graph.add_node(retrieve_policy)
    graph.add_node(draft_email)
    graph.add_edge(START, "retrieve_policy")
    graph.add_edge("retrieve_policy", "draft_email")
    graph.add_edge("draft_email", END)
    return graph.compile()


_EMAIL_GRAPH = _build_email_graph()


def run_email_draft(customer_message: str) -> dict[str, Any]:
    initial: SupportState = {
        "customer_message": customer_message,
        "intent": "email_draft",
        "retrieved_contexts": [],
        "draft_response": "",
        "citations": [],
        "confidence_label": "low",
        "requires_human_approval": True,
        "final_response": "",
    }
    final: dict[str, Any] = {}
    for event in _EMAIL_GRAPH.stream(initial):
        for node_output in event.values():
            if isinstance(node_output, dict):
                final.update(node_output)
    return final
