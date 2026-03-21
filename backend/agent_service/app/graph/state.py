from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    conversation_id: str
    assistant_message_id: str
    query: str
    params: dict[str, Any]
    scenario_id: str
    normalized_intent: str
    normalized_context: dict[str, Any]
    documents: list[dict[str, Any]]
    evidence: dict[str, Any]
    outline: str
    section_order: list[str]
    section_contents: dict[str, str]
    current_section_title: str
    generated_sections_context: str
    summary: str
    final_markdown: str
    evidence_cards: list[dict[str, Any]]
    assumptions: list[str]
    metadata: dict[str, Any]
    status: str
    errors: list[str]
