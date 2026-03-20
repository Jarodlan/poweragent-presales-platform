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
