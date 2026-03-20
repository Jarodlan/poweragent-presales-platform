from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from apps.conversations.models import Conversation, Message

from .models import Task, TaskEvent


def create_generation_task(
    *,
    conversation: Conversation,
    assistant_message: Message,
    query: str,
    params: dict[str, Any],
) -> Task:
    task = Task.objects.create(
        conversation=conversation,
        assistant_message=assistant_message,
        status="running",
        current_step="queued",
        request_payload={"query": query, "params": params},
        started_at=timezone.now(),
    )

    payload = {
        "task_id": str(task.id),
        "conversation_id": str(conversation.id),
        "assistant_message_id": str(assistant_message.id),
        "query": query,
        "params": params,
        "callback_url": f"{settings.PLATFORM_BASE_URL}/api/v1/internal/agent/task-callbacks/{task.id}",
    }

    try:
        response = requests.post(
            f"{settings.AGENT_SERVICE_BASE_URL}/internal/agent/runs",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        task.run_id = data.get("run_id", "")
        task.current_step = data.get("status", "started")
        task.save(update_fields=["run_id", "current_step", "updated_at"])
    except Exception as exc:
        task.status = "failed"
        task.error_code = "AGENT_START_FAILED"
        task.error_message = str(exc)
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "error_code", "error_message", "finished_at", "updated_at"])

    TaskEvent.objects.create(task=task, event_type="task_created", payload_json=payload)
    return task


def apply_agent_callback(
    *,
    task: Task,
    status_value: str,
    current_step: str,
    result: dict[str, Any] | None,
    error_code: str = "",
    error_message: str = "",
) -> Task:
    assistant_message = task.assistant_message
    conversation = task.conversation

    task.status = status_value
    task.current_step = current_step
    task.error_code = error_code
    task.error_message = error_message
    if result:
        task.result_payload = result

    if status_value in {"completed", "failed", "cancelled"}:
        task.finished_at = timezone.now()

    if status_value == "completed" and result:
        assistant_message.status = "completed"
        assistant_message.summary_text = result.get("summary", "")
        assistant_message.content_markdown = result.get("final_markdown", "")
        assistant_message.assumptions_json = result.get("assumptions", [])
        assistant_message.evidence_cards_json = result.get("evidence_cards", [])
        assistant_message.metadata_json = {
            "normalized_intent": result.get("normalized_intent", ""),
            "normalized_context": result.get("normalized_context", {}),
        }
        assistant_message.save(
            update_fields=[
                "status",
                "summary_text",
                "content_markdown",
                "assumptions_json",
                "evidence_cards_json",
                "metadata_json",
                "updated_at",
            ]
        )
        conversation.status = "idle"
    elif status_value == "failed":
        assistant_message.status = "failed"
        assistant_message.content_markdown = error_message or "任务执行失败"
        assistant_message.save(update_fields=["status", "content_markdown", "updated_at"])
        conversation.status = "failed"
    else:
        assistant_message.status = "running"
        assistant_message.save(update_fields=["status", "updated_at"])
        conversation.status = "running"

    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=["status", "last_message_at", "updated_at"])
    task.save(
        update_fields=[
            "status",
            "current_step",
            "error_code",
            "error_message",
            "result_payload",
            "finished_at",
            "updated_at",
        ]
    )
    TaskEvent.objects.create(
        task=task,
        event_type="agent_callback",
        payload_json={
            "status": status_value,
            "current_step": current_step,
            "error_code": error_code,
            "error_message": error_message,
        },
    )
    return task
