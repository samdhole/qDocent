"""Support triage LangGraph workflow.

Flow:
  classify_intent → retrieve_context → check_approval → send_response

Human approval gate: check_approval sets requires_human_approval=True when needed.
send_response always sets final_response to the draft — no placeholder string.
The caller inspects requires_human_approval and must gate before acting on the response.
Note: no LangGraph checkpointer is wired; the graph always runs to completion.

Nodes are pure functions. No side effects except retrieve_context (R2R call).
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
from packages.workflows.approval_policy import requires_approval
from packages.workflows.state import SupportState

load_dotenv()

_LLM_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gemini-3-flash-preview")

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
    """Retrieve relevant policy chunks from R2R via the shared r2r_client boundary."""
    log = logging.getLogger(__name__)
    try:
        result = r2r_client.rag_query(query=state["customer_message"])
    except Exception as exc:
        log.warning("R2R retrieval failed: %s", exc, exc_info=True)
        result = {"retrieved_contexts": [], "citations": [], "answer": "", "confidence_label": "low"}
    return {
        **state,
        "retrieved_contexts": result["retrieved_contexts"],
        "citations": result["citations"],
        "draft_response": result["answer"],
        "confidence_label": result["confidence_label"],
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
    """Set final_response to the draft. requires_human_approval is advisory — the caller
    must check it before acting. No in-process blocking without a LangGraph checkpointer.
    """
    return {**state, "final_response": state["draft_response"]}


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
    # this demo doesn't wire up. requires_human_approval is advisory; the caller gates.
    return graph.compile()


_GRAPH = _build_graph()  # Built once at import — R2R/LLM deps must be importable at module load


def run_support_triage(customer_message: str) -> dict[str, Any]:
    """Run the support triage workflow and return the final state dict.

    final_response always contains the draft answer. When requires_human_approval is True,
    the caller must gate before surfacing or acting on the response.
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
