import json
import time

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Message

from .models import Task, TaskEvent
from .serializers import TaskSerializer


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
        task = Task.objects.get(id=task_id)

        def stream():
            payload = {
                "conversation_id": str(task.conversation_id),
                "assistant_message_id": str(task.assistant_message_id),
                "task_id": str(task.id),
                "step": task.current_step or "running",
                "message": "正在执行工作流",
                "progress": 10,
            }
            yield f"data: {json.dumps({'event': 'status', 'data': payload}, ensure_ascii=False)}\n\n"

            # Skeleton implementation: stream currently emits cached result when available.
            if task.result_payload:
                summary = task.result_payload.get("summary", "")
                content = task.result_payload.get("final_markdown", "")
                if summary:
                    yield f"data: {json.dumps({'event': 'summary_chunk', 'data': {'task_id': str(task.id), 'content': summary}}, ensure_ascii=False)}\n\n"
                if content:
                    yield f"data: {json.dumps({'event': 'content_chunk', 'data': {'task_id': str(task.id), 'content': content}}, ensure_ascii=False)}\n\n"
            else:
                assistant_message = Message.objects.get(id=task.assistant_message_id)
                if assistant_message.summary_text:
                    yield f"data: {json.dumps({'event': 'summary_chunk', 'data': {'task_id': str(task.id), 'content': assistant_message.summary_text}}, ensure_ascii=False)}\n\n"
                if assistant_message.content_markdown:
                    yield f"data: {json.dumps({'event': 'content_chunk', 'data': {'task_id': str(task.id), 'content': assistant_message.content_markdown}}, ensure_ascii=False)}\n\n"

            time.sleep(0.05)
            yield f"data: {json.dumps({'event': 'completed', 'data': {'task_id': str(task.id), 'status': task.status}}, ensure_ascii=False)}\n\n"

        return StreamingHttpResponse(stream(), content_type="text/event-stream")
