from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    conversation_id: str
    assistant_message_id: str
    query: str
    params: dict[str, Any]
    normalized_intent: str
    normalized_context: dict[str, Any]
    evidence: dict[str, Any]
    outline: str
    summary: str
    final_markdown: str
    evidence_cards: list[dict[str, Any]]
    assumptions: list[str]
    metadata: dict[str, Any]
    status: str
    errors: list[str]
