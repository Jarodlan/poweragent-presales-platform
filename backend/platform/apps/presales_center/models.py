from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import Department


class PresalesTask(models.Model):
    TASK_TYPE_CHOICES = [
        ("follow_up", "FollowUp"),
        ("proposal_review", "ProposalReview"),
        ("customer_revisit", "CustomerRevisit"),
        ("internal_alignment", "InternalAlignment"),
        ("materials_prepare", "MaterialsPrepare"),
        ("manual", "Manual"),
    ]
    SOURCE_TYPE_CHOICES = [
        ("customer_demand_report", "CustomerDemandReport"),
        ("solution_result", "SolutionResult"),
        ("manual", "Manual"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "InProgress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("reassigned", "Reassigned"),
        ("archived", "Archived"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    FOLLOWUP_STATUS_CHOICES = [
        ("not_scheduled", "NotScheduled"),
        ("scheduled", "Scheduled"),
        ("done", "Done"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]
    FEISHU_DELIVERY_STATUS_CHOICES = [
        ("not_sent", "NotSent"),
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("partial", "Partial"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_title = models.CharField(max_length=255)
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES, default="follow_up")
    task_description = models.TextField(blank=True)
    source_type = models.CharField(max_length=64, choices=SOURCE_TYPE_CHOICES, default="manual")
    source_id = models.CharField(max_length=128, blank=True)
    source_version = models.PositiveIntegerField(null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True)
    customer_id = models.CharField(max_length=128, blank=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_presales_tasks",
    )
    owner_department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_presales_tasks",
    )
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_presales_tasks",
    )
    collaborator_user_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium")
    due_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    followup_status = models.CharField(max_length=32, choices=FOLLOWUP_STATUS_CHOICES, default="not_scheduled")
    feishu_delivery_status = models.CharField(max_length=32, choices=FEISHU_DELIVERY_STATUS_CHOICES, default="not_sent")
    latest_feishu_delivery = models.ForeignKey(
        "FeishuDeliveryRecord",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="latest_for_tasks",
    )
    payload_json = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_presales_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["assignee_user", "status", "due_at"]),
            models.Index(fields=["owner_department", "status", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["customer_name", "created_at"]),
            models.Index(fields=["next_follow_up_at", "followup_status"]),
            models.Index(fields=["feishu_delivery_status", "updated_at"]),
        ]


class PresalesTaskActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("assigned", "Assigned"),
        ("status_changed", "StatusChanged"),
        ("due_changed", "DueChanged"),
        ("followup_scheduled", "FollowupScheduled"),
        ("followup_completed", "FollowupCompleted"),
        ("feishu_sent", "FeishuSent"),
        ("feishu_failed", "FeishuFailed"),
        ("archive_created", "ArchiveCreated"),
        ("reassigned", "Reassigned"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(PresalesTask, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=32, choices=ACTIVITY_TYPE_CHOICES)
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="presales_task_activities",
    )
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    summary = models.CharField(max_length=255)
    details_markdown = models.TextField(blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["activity_type", "created_at"]),
            models.Index(fields=["operator_user", "created_at"]),
        ]


class PresalesArchiveRecord(models.Model):
    ARCHIVE_TYPE_CHOICES = [
        ("meeting_recording", "MeetingRecording"),
        ("demand_report", "DemandReport"),
        ("stage_summary", "StageSummary"),
        ("solution_markdown", "SolutionMarkdown"),
        ("solution_html", "SolutionHtml"),
        ("solution_pdf", "SolutionPdf"),
        ("attachment", "Attachment"),
    ]
    STORAGE_PROVIDER_CHOICES = [
        ("local", "Local"),
        ("s3", "S3"),
        ("oss", "OSS"),
        ("cos", "COS"),
    ]
    ARCHIVE_STATUS_CHOICES = [
        ("active", "Active"),
        ("deleted", "Deleted"),
        ("orphaned", "Orphaned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archive_type = models.CharField(max_length=32, choices=ARCHIVE_TYPE_CHOICES)
    source_type = models.CharField(max_length=64)
    source_id = models.CharField(max_length=128, blank=True)
    source_version = models.PositiveIntegerField(null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True)
    source_title = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    storage_provider = models.CharField(max_length=32, choices=STORAGE_PROVIDER_CHOICES, default="local")
    storage_path = models.CharField(max_length=500)
    storage_bucket = models.CharField(max_length=128, blank=True)
    archive_status = models.CharField(max_length=32, choices=ARCHIVE_STATUS_CHOICES, default="active")
    feishu_shared = models.BooleanField(default=False)
    metadata_json = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_presales_archives",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["archive_type", "created_at"]),
            models.Index(fields=["customer_name", "created_at"]),
            models.Index(fields=["archive_status", "updated_at"]),
        ]


class PresalesFollowupReminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ("task_due", "TaskDue"),
        ("task_overdue", "TaskOverdue"),
        ("follow_up", "FollowUp"),
        ("manual", "Manual"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("superseded", "Superseded"),
    ]
    CHANNEL_CHOICES = [("feishu", "Feishu"), ("platform", "Platform")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(PresalesTask, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=32, choices=REMINDER_TYPE_CHOICES)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presales_reminders")
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    channel = models.CharField(max_length=32, choices=CHANNEL_CHOICES, default="feishu")
    latest_delivery = models.ForeignKey(
        "FeishuDeliveryRecord",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reminder_latest_for",
    )
    payload_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at", "created_at"]
        indexes = [
            models.Index(fields=["scheduled_at", "status"]),
            models.Index(fields=["target_user", "status"]),
            models.Index(fields=["task", "reminder_type"]),
        ]


class FeishuDeliveryRecord(models.Model):
    TARGET_TYPE_CHOICES = [("user", "User"), ("group", "Group"), ("department_owner", "DepartmentOwner")]
    MESSAGE_TYPE_CHOICES = [("text", "Text"), ("post", "Post"), ("interactive_card", "InteractiveCard")]
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("partial", "Partial"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_type = models.CharField(max_length=64)
    business_id = models.CharField(max_length=128, blank=True)
    target_type = models.CharField(max_length=32, choices=TARGET_TYPE_CHOICES)
    target_id = models.CharField(max_length=128)
    target_name = models.CharField(max_length=255, blank=True)
    message_type = models.CharField(max_length=32, choices=MESSAGE_TYPE_CHOICES, default="text")
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    delivery_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="queued")
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="presales_feishu_deliveries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business_type", "business_id"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["delivery_status", "created_at"]),
            models.Index(fields=["operator_user", "created_at"]),
        ]


class FeishuSyncJob(models.Model):
    JOB_TYPE_CHOICES = [
        ("sync_departments", "SyncDepartments"),
        ("sync_users", "SyncUsers"),
        ("full_sync", "FullSync"),
        ("offboarding_reconcile", "OffboardingReconcile"),
    ]
    TRIGGER_TYPE_CHOICES = [("scheduled", "Scheduled"), ("manual", "Manual"), ("startup", "Startup")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("partial", "Partial"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=32, choices=JOB_TYPE_CHOICES)
    trigger_type = models.CharField(max_length=32, choices=TRIGGER_TYPE_CHOICES, default="manual")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    synced_user_count = models.PositiveIntegerField(default=0)
    synced_department_count = models.PositiveIntegerField(default=0)
    disabled_user_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    summary_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="presales_feishu_sync_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["trigger_type", "created_at"]),
        ]
