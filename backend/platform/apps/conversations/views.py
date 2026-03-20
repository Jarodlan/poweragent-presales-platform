from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.services import create_generation_task

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationListCreateView(APIView):
    def get(self, request):
        qs = Conversation.objects.all()[:20]
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "items": ConversationSerializer(qs, many=True).data,
                    "page": 1,
                    "page_size": 20,
                    "has_more": False,
                },
            }
        )

    def post(self, request):
        conversation = Conversation.objects.create(title=request.data.get("title", ""))
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": ConversationSerializer(conversation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    def get(self, request, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": ConversationSerializer(conversation).data,
            }
        )


class ConversationMessagesView(APIView):
    def get(self, request, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        messages = conversation.messages.all()[:50]
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "conversation_id": str(conversation.id),
                    "items": MessageSerializer(messages, many=True).data,
                    "page": 1,
                    "page_size": 50,
                    "has_more": False,
                },
            }
        )

    def post(self, request, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        query = request.data.get("query", "").strip()
        params = request.data.get("params", {})

        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            status="completed",
            query_text=query,
            content_markdown=query,
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            status="pending",
        )

        conversation.last_user_message = query
        conversation.last_message_at = timezone.now()
        conversation.status = "running"
        if not conversation.title:
            conversation.title = query[:40]
        conversation.save(update_fields=["last_user_message", "last_message_at", "status", "title", "updated_at"])

        task = create_generation_task(
            conversation=conversation,
            assistant_message=assistant_message,
            query=query,
            params=params,
        )

        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "conversation_id": str(conversation.id),
                    "user_message_id": str(user_message.id),
                    "assistant_message_id": str(assistant_message.id),
                    "task_id": str(task.id),
                    "status": task.status,
                    "stream_url": f"/api/v1/solution/tasks/{task.id}/stream",
                    "result_url": f"/api/v1/solution/tasks/{task.id}",
                },
            },
            status=status.HTTP_201_CREATED,
        )
