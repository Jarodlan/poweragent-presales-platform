from rest_framework import serializers

from .models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    conversation_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "conversation_id",
            "title",
            "status",
            "last_user_message",
            "last_message_at",
            "crm_provider",
            "crm_base_id",
            "crm_customer_record_id",
            "crm_customer_snapshot",
            "crm_opportunity_record_id",
            "crm_opportunity_snapshot",
            "crm_bound_at",
            "crm_last_writeback_at",
            "crm_last_writeback_status",
            "created_at",
            "updated_at",
        ]


class MessageSerializer(serializers.ModelSerializer):
    message_id = serializers.UUIDField(source="id", read_only=True)
    conversation_id = serializers.UUIDField(source="conversation.id", read_only=True)
    summary = serializers.CharField(source="summary_text", read_only=True)
    content = serializers.CharField(source="content_markdown", read_only=True)
    assumptions = serializers.JSONField(source="assumptions_json", read_only=True)
    evidence_cards = serializers.JSONField(source="evidence_cards_json", read_only=True)

    class Meta:
        model = Message
        fields = [
            "message_id",
            "conversation_id",
            "role",
            "status",
            "query_text",
            "summary",
            "content",
            "assumptions",
            "evidence_cards",
            "created_at",
        ]
