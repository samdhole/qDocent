"""Support triage LangGraph workflow.

Flow:
  classify_intent → retrieve_context → draft_response → check_approval → send_response

Human approval gate: send_response checks requires_human_approval and sets
final_response to "[Awaiting human approval]" when True. The caller inspects
this field and must not send the response until a human approves.

Nodes are pure functions. No side effects except retrieve_context (R2R call).
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
from shared.abstractions.exception import R2RException

from packages.workflows.approval_policy import (
    confidence_from_contexts,
    requires_approval,
)
from packages.workflows.state import SupportState

load_dotenv()

_R2R_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
_LLM_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gemini-3-flash-preview")
_SEARCH_SETTINGS: dict[str, Any] = {
    "limit": 5,
    "graph_settings": {"enabled": False},
}

# Intent keywords for rule-based classification (part of the 60% deterministic budget)
_INTENT_RULES: list[tuple[str, str]] = [
    ("refund|return|money back", "refund_request"),
    ("discount|pricing|enterprise plan|quote", "pricing_inquiry"),
    ("cancel|terminate|close account", "cancellation_request"),
    ("support|help|issue|problem|bug|error", "support_request"),
    ("policy|procedure|guideline|rule", "policy_lookup"),
]


# ── Nodes ────────────────────────────────────────────────────────────────────

def classify_intent(state: SupportState) -> SupportState:
    """Classify customer intent from the message. Rule-based first, LLM fallback."""
    import re
    msg = state["customer_message"].lower()
    for pattern, intent in _INTENT_RULES:
        if re.search(pattern, msg):
            return {**state, "intent": intent}
    # LLM fallback — only if API key is available; otherwise default to "general"
    if not os.getenv("GOOGLE_API_KEY"):
        return {**state, "intent": "general"}
    llm = ChatGoogleGenerativeAI(model=_LLM_MODEL, temperature=0)
    prompt = (
        f"Classify this customer message into one of: refund_request, pricing_inquiry, "
        f"cancellation_request, support_request, policy_lookup, or general.\n"
        f"Message: {state['customer_message']}\nIntent:"
    )
    raw = llm.invoke(prompt).content
    text = raw[0].get("text", "") if isinstance(raw, list) else raw
    intent = text.strip().split()[0]
    return {**state, "intent": intent}


def retrieve_context(state: SupportState) -> SupportState:
    """Retrieve relevant policy chunks from R2R."""
    log = logging.getLogger(__name__)
    try:
        client = R2RClient(base_url=_R2R_URL)
        response = client.retrieval.rag(
            query=state["customer_message"],
            search_settings=_SEARCH_SETTINGS,
        )
        inner = getattr(response, "results", response)
        agg = getattr(inner, "search_results", None)
        search_results = getattr(agg, "chunk_search_results", None) or [] if agg else []
        retrieved_contexts = [
            {
                "chunk_id": getattr(r, "id", None),
                "text": getattr(r, "text", "")[:400],
                "score": round(getattr(r, "score", 0.0) or 0.0, 4),
            }
            for r in search_results
        ]
        citations = [
            {
                "document": (getattr(r, "metadata", {}) or {}).get("source_file", "unknown"),
                "page": (getattr(r, "metadata", {}) or {}).get("page_start"),
                "chunk_id": getattr(r, "id", None),
            }
            for r in search_results
        ]
        answer = getattr(inner, "generated_answer", "") or ""
    except (httpx.ConnectError, httpx.HTTPStatusError, httpx.TimeoutException, R2RException) as exc:
        log.warning("R2R retrieval failed: %s", exc, exc_info=True)
        retrieved_contexts = []
        citations = []
        answer = ""

    confidence_label = confidence_from_contexts(retrieved_contexts)
    return {
        **state,
        "retrieved_contexts": retrieved_contexts,
        "citations": citations,
        "draft_response": answer,
        "confidence_label": confidence_label,
    }


def check_approval(state: SupportState) -> SupportState:
    """Determine whether human approval is required before sending."""
    needs_approval = requires_approval(
        draft_response=state["draft_response"],
        citations=state["citations"],
        confidence_label=state["confidence_label"],
        proposes_external_action=False,
    )
    return {**state, "requires_human_approval": needs_approval}


def send_response(state: SupportState) -> SupportState:
    """Set final_response. In-node guard: approval-required cases return a
    placeholder string; callers must check requires_human_approval before using.
    """
    if state["requires_human_approval"]:
        final = "[Awaiting human approval]"
    else:
        final = state["draft_response"]
    return {**state, "final_response": final}


# ── Graph ────────────────────────────────────────────────────────────────────

def _build_graph() -> Any:
    graph = StateGraph(SupportState)
    graph.add_node(classify_intent)
    graph.add_node(retrieve_context)
    graph.add_node(check_approval)
    graph.add_node(send_response)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "retrieve_context")
    graph.add_edge("retrieve_context", "check_approval")
    graph.add_edge("check_approval", "send_response")
    graph.add_edge("send_response", END)

    # No interrupt_before — requires a LangGraph checkpointer to function, which
    # this demo doesn't wire up. The approval gate is enforced in send_response().
    return graph.compile()


_GRAPH = _build_graph()  # Built once at import — R2R/LLM deps must be importable at module load


def run_support_triage(customer_message: str) -> dict[str, Any]:
    """Run the support triage workflow and return the final state dict.

    When requires_human_approval is True, final_response is '[Awaiting human approval]'.
    The caller must check this field before surfacing the response to users.
    """
    initial_state: SupportState = {
        "customer_message": customer_message,
        "intent": "",
        "retrieved_contexts": [],
        "draft_response": "",
        "citations": [],
        "confidence_label": "low",
        "requires_human_approval": False,
        "final_response": "",
    }
    final: dict[str, Any] = {}
    for event in _GRAPH.stream(initial_state):
        for node_output in event.values():
            if isinstance(node_output, dict):
                final.update(node_output)
    return final
