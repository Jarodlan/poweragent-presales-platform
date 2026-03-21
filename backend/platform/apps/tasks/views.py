import json
import time

import requests
from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Message

from .models import Task, TaskEvent
from .progress import describe_step
from .serializers import TaskSerializer
from .services import apply_agent_callback


def fetch_agent_run_status(run_id: str) -> dict | None:
    if not run_id:
        return None
    try:
        response = requests.get(
            f"{settings.AGENT_SERVICE_BASE_URL}/internal/agent/runs/{run_id}",
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


class TaskResultView(APIView):
    def get(self, request, task_id):
        task = Task.objects.get(id=task_id)
        data = TaskSerializer(task).data
        data["conversation_id"] = str(task.conversation_id)
        data["assistant_message_id"] = str(task.assistant_message_id)
        return Response({"code": 0, "message": "ok", "data": data})


class TaskCancelView(APIView):
    def post(self, request, task_id):
        task = Task.objects.get(id=task_id)
        task.status = "cancelled"
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at", "updated_at"])
        TaskEvent.objects.create(task=task, event_type="task_cancelled", payload_json={})
        return Response({"code": 0, "message": "ok", "data": {"task_id": str(task.id), "status": task.status}})


class TaskStreamView(APIView):
    def get(self, request, task_id):
        def stream():
            last_step = None
            last_status = None
            last_progress = None
            content_sent = False

            task = Task.objects.get(id=task_id)
            yield f"data: {json.dumps({'event': 'conversation_meta', 'data': {'conversation_id': str(task.conversation_id), 'title': task.conversation.title}}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'event': 'message_created', 'data': {'conversation_id': str(task.conversation_id), 'assistant_message_id': str(task.assistant_message_id)}}, ensure_ascii=False)}\n\n"

            for _ in range(1800):
                task = Task.objects.get(id=task_id)
                assistant_message = Message.objects.get(id=task.assistant_message_id)
                agent_status = None
                current_status = task.status
                current_step = task.current_step or "running"

                if task.status not in {"completed", "failed", "cancelled"} and task.run_id:
                    agent_status = fetch_agent_run_status(task.run_id)
                    if agent_status:
                        current_status = agent_status.get("status") or current_status
                        current_step = agent_status.get("step") or current_step

                if agent_status:
                    message = agent_status.get("step_label") or describe_step(current_step, current_status)["label"]
                    progress = agent_status.get("progress", describe_step(current_step, current_status)["progress"])
                else:
                    progress_meta = describe_step(current_step, current_status)
                    message = progress_meta["label"]
                    progress = progress_meta["progress"]

                if current_step != last_step or current_status != last_status or progress != last_progress:
                    payload = {
                        "conversation_id": str(task.conversation_id),
                        "assistant_message_id": str(task.assistant_message_id),
                        "task_id": str(task.id),
                        "step": current_step,
                        "message": message,
                        "progress": progress,
                    }
                    yield f"data: {json.dumps({'event': 'status', 'data': payload}, ensure_ascii=False)}\n\n"
                    last_step = current_step
                    last_status = current_status
                    last_progress = progress

                if task.status in {"completed", "failed", "cancelled"} and not content_sent:
                    if assistant_message.summary_text:
                        yield f"data: {json.dumps({'event': 'summary_chunk', 'data': {'task_id': str(task.id), 'content': assistant_message.summary_text}}, ensure_ascii=False)}\n\n"
                    if assistant_message.content_markdown:
                        yield f"data: {json.dumps({'event': 'content_chunk', 'data': {'task_id': str(task.id), 'content': assistant_message.content_markdown}}, ensure_ascii=False)}\n\n"
                    if assistant_message.evidence_cards_json:
                        yield f"data: {json.dumps({'event': 'evidence_cards', 'data': {'task_id': str(task.id), 'items': assistant_message.evidence_cards_json}}, ensure_ascii=False)}\n\n"
                    content_sent = True

                if task.status in {"completed", "failed", "cancelled"}:
                    yield f"data: {json.dumps({'event': 'completed', 'data': {'task_id': str(task.id), 'status': task.status}}, ensure_ascii=False)}\n\n"
                    break

                time.sleep(0.5)
            else:
                yield f"data: {json.dumps({'event': 'error', 'data': {'task_id': str(task_id), 'code': 50002, 'message': '任务执行时间较长，请稍后查看结果'}}, ensure_ascii=False)}\n\n"

        return StreamingHttpResponse(stream(), content_type="text/event-stream")


class AgentTaskCallbackView(APIView):
    def post(self, request, task_id):
        task = Task.objects.get(id=task_id)
        apply_agent_callback(
            task=task,
            status_value=request.data.get("status", "failed"),
            current_step=request.data.get("current_step", ""),
            result=request.data.get("result"),
            error_code=request.data.get("error_code", ""),
            error_message=request.data.get("error_message", ""),
        )
        return Response({"code": 0, "message": "ok", "data": {"task_id": str(task.id)}}, status=status.HTTP_200_OK)
