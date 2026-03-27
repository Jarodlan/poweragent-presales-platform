import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("running", "Running"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="idle")
    last_user_message = models.TextField(blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    crm_provider = models.CharField(max_length=32, blank=True)
    crm_base_id = models.CharField(max_length=128, blank=True)
    crm_customer_record_id = models.CharField(max_length=128, blank=True)
    crm_customer_snapshot = models.JSONField(default=dict, blank=True)
    crm_opportunity_record_id = models.CharField(max_length=128, blank=True)
    crm_opportunity_snapshot = models.JSONField(default=dict, blank=True)
    crm_bound_at = models.DateTimeField(null=True, blank=True)
    crm_last_writeback_at = models.DateTimeField(null=True, blank=True)
    crm_last_writeback_status = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["crm_customer_record_id"]),
            models.Index(fields=["crm_opportunity_record_id"]),
        ]


class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="completed")
    query_text = models.TextField(blank=True)
    summary_text = models.TextField(blank=True)
    content_markdown = models.TextField(blank=True)
    assumptions_json = models.JSONField(default=list, blank=True)
    evidence_cards_json = models.JSONField(default=list, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
