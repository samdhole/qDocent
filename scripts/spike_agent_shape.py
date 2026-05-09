"""Spike: confirm streaming agent event shapes. Delete after Phase 4."""
from r2r import R2RClient

client = R2RClient(base_url="http://localhost:7272")

# Create a conversation
conv = client.conversations.create(name="stream-spike")
conv_dict = conv.model_dump() if hasattr(conv, "model_dump") else conv
conversation_id = (conv_dict.get("results") or {}).get("id") or conv_dict.get("id")
print(f"conversation_id: {conversation_id}")

# Stream agent events
stream = client.retrieval.agent(
    message={"role": "user", "content": "What's in the document?"},
    conversation_id=conversation_id,
    search_settings={"limit": 5, "graph_settings": {"enabled": False}},
    rag_generation_config={"stream": True},
)

print("\nStreaming events:")
for event in stream:
    event_type = type(event).__name__
    payload = event.model_dump() if hasattr(event, "model_dump") else event
    print(f"\n{event_type}:")
    print(f"  payload keys: {payload.keys() if isinstance(payload, dict) else 'N/A'}")
    if event_type == "SearchResultsEvent":
        print(f"  data.chunk_search_results: {type((payload.get('data') or {}).get('chunk_search_results'))}")
    elif event_type == "MessageEvent":
        data = (payload.get("data") or {})
        delta = data.get("delta") or {}
        content = delta.get("content") or []
        print(f"  data.delta.content[0] type: {type(content[0]) if content else 'empty'}")
        if content:
            print(f"  data.delta.content[0].payload.value: {content[0].get('payload', {}).get('value') if isinstance(content[0], dict) else 'N/A'}")
    elif event_type == "FinalAnswerEvent":
        data = (payload.get("data") or {})
        print(f"  data.generated_answer: {bool(data.get('generated_answer'))}")
        print(f"  data.conversation_id: {data.get('conversation_id')}")

print("\nStream complete.")
