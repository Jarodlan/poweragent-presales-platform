from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class CrmWritebackRecord(models.Model):
    PROVIDER_CHOICES = [("feishu_bitable", "FeishuBitable")]
    OBJECT_TYPE_CHOICES = [
        ("customer_demand_session", "CustomerDemandSession"),
        ("customer_demand_report", "CustomerDemandReport"),
        ("solution_conversation", "SolutionConversation"),
        ("solution_result", "SolutionResult"),
        ("presales_task", "PresalesTask"),
        ("archive_record", "ArchiveRecord"),
    ]
    TARGET_TABLE_CHOICES = [
        ("customer", "Customer"),
        ("opportunity", "Opportunity"),
        ("followup", "Followup"),
        ("attachment", "Attachment"),
    ]
    ACTION_CHOICES = [
        ("bind", "Bind"),
        ("create_record", "CreateRecord"),
        ("update_record", "UpdateRecord"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default="feishu_bitable")
    object_type = models.CharField(max_length=64, choices=OBJECT_TYPE_CHOICES)
    object_id = models.CharField(max_length=128)
    target_table = models.CharField(max_length=32, choices=TARGET_TABLE_CHOICES)
    target_record_id = models.CharField(max_length=128, blank=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_writeback_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id", "created_at"]),
            models.Index(fields=["target_table", "status", "created_at"]),
            models.Index(fields=["provider", "created_at"]),
        ]
