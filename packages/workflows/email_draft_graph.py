"""Email draft workflow — retrieves policy, drafts an email, always requires approval.

Proposing to send an email is an external action → requires_human_approval always True.
This is a simplified graph for demo purposes.
"""
# pattern: Imperative Shell
from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from apps.api.services import r2r_client
from packages.workflows.state import SupportState

load_dotenv()

_LLM_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gemini-3-flash-preview")


def retrieve_policy(state: SupportState) -> SupportState:
    """Retrieve relevant policy chunks from R2R via the shared r2r_client boundary."""
    log = logging.getLogger(__name__)
    try:
        result = r2r_client.rag_query(query=state["customer_message"])
    except Exception as exc:
        log.warning("R2R retrieval failed: %s", exc, exc_info=True)
        result = {"retrieved_contexts": [], "citations": [], "answer": "", "confidence_label": "low"}
    return {**state, "retrieved_contexts": result["retrieved_contexts"], "citations": result["citations"]}


def _fallback_email_draft(customer_message: str, contexts: list[dict[str, Any]]) -> str:
    policy_context = contexts[0]["text"] if contexts else "No matching policy context was found."
    return (
        "Subject: Follow-up on your request\n\n"
        "Hello,\n\n"
        "Thanks for reaching out. I reviewed the available policy context for your request:\n\n"
        f"{policy_context}\n\n"
        "Based on that context, I would reply carefully and ask a teammate to confirm before sending.\n\n"
        f"Customer message: {customer_message}\n\n"
        "Best,\nSupport Team"
    )


def draft_email(state: SupportState) -> SupportState:
    """Draft a polite email response using LLM. Always sets approval required."""
    context_text = "\n".join(c["text"] for c in state["retrieved_contexts"][:3])
    if os.getenv("GOOGLE_API_KEY"):
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
    else:
        draft = _fallback_email_draft(state["customer_message"], state["retrieved_contexts"])
    confidence = "medium" if state["retrieved_contexts"] else "low"
    return {
        **state,
        "draft_response": draft,
        "confidence_label": confidence,
        "requires_human_approval": True,  # Always — email send is an external action
        "final_response": draft,
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
