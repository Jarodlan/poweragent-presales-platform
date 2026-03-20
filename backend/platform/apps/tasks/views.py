import json
import time

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
            content_sent = False

            task = Task.objects.get(id=task_id)
            yield f"data: {json.dumps({'event': 'conversation_meta', 'data': {'conversation_id': str(task.conversation_id), 'title': task.conversation.title}}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'event': 'message_created', 'data': {'conversation_id': str(task.conversation_id), 'assistant_message_id': str(task.assistant_message_id)}}, ensure_ascii=False)}\n\n"

            for _ in range(240):
                task = Task.objects.get(id=task_id)
                assistant_message = Message.objects.get(id=task.assistant_message_id)

                if task.current_step != last_step or task.status != last_status:
                    progress_meta = describe_step(task.current_step or "running", task.status)
                    payload = {
                        "conversation_id": str(task.conversation_id),
                        "assistant_message_id": str(task.assistant_message_id),
                        "task_id": str(task.id),
                        "step": task.current_step or "running",
                        "message": progress_meta["label"],
                        "progress": progress_meta["progress"],
                    }
                    yield f"data: {json.dumps({'event': 'status', 'data': payload}, ensure_ascii=False)}\n\n"
                    last_step = task.current_step
                    last_status = task.status

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
                yield f"data: {json.dumps({'event': 'error', 'data': {'task_id': str(task_id), 'code': 50002, 'message': '任务等待超时'}}, ensure_ascii=False)}\n\n"

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
