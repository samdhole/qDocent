"""One-off spike: dump raw R2R agent() response shape. Delete after Phase 3."""
import json
import sys

from r2r import R2RClient

client = R2RClient(base_url="http://localhost:7272")

# Create a conversation
conv = client.conversations.create(name="spike")
conv_dict = conv.model_dump() if hasattr(conv, "model_dump") else conv
conversation_id = (conv_dict.get("results") or {}).get("id") or conv_dict.get("id")
print(f"conversation_id: {conversation_id}")

# Send a message
response = client.retrieval.agent(
    message={"role": "user", "content": "What does the document say?"},
    conversation_id=conversation_id,
    search_settings={"limit": 5, "graph_settings": {"enabled": False}},
)
data = response.model_dump() if hasattr(response, "model_dump") else response
sys.stdout.write(json.dumps(data, indent=2, default=str))
