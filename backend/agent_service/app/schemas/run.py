from typing import Any

from pydantic import BaseModel, Field


class AgentRunCreateRequest(BaseModel):
    task_id: str
    conversation_id: str
    assistant_message_id: str
    query: str
    params: dict[str, Any] = Field(default_factory=dict)
    callback_url: str


class AgentRunResponse(BaseModel):
    run_id: str
    status: str


class AgentRunStatusResponse(BaseModel):
    run_id: str
    status: str
    step: str
    result: dict[str, Any] | None = None
