from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import Department


class CustomerDemandSession(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("recording", "Recording"),
        ("paused", "Paused"),
        ("closed", "Closed"),
        ("analyzing", "Analyzing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_demand_sessions",
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_demand_sessions",
    )
    customer_name = models.CharField(max_length=200)
    session_title = models.CharField(max_length=255)
    industry = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    customer_type = models.CharField(max_length=50, blank=True)
    knowledge_enabled = models.BooleanField(default=False)
    knowledge_scope = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    recording_started_at = models.DateTimeField(null=True, blank=True)
    recording_stopped_at = models.DateTimeField(null=True, blank=True)
    analysis_started_at = models.DateTimeField(null=True, blank=True)
    analysis_finished_at = models.DateTimeField(null=True, blank=True)
    raw_segment_count = models.PositiveIntegerField(default=0)
    normalized_segment_count = models.PositiveIntegerField(default=0)
    latest_stage_version = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["owner", "-updated_at"]),
            models.Index(fields=["department", "-updated_at"]),
            models.Index(fields=["status", "-updated_at"]),
            models.Index(fields=["customer_name"]),
            models.Index(fields=["industry"]),
            models.Index(fields=["region"]),
        ]

    def __str__(self) -> str:
        return self.session_title


class CustomerDemandParticipant(models.Model):
    PARTICIPANT_TYPE_CHOICES = [
        ("customer", "Customer"),
        ("sales", "Sales"),
        ("presales", "PreSales"),
        ("tech_support", "TechSupport"),
        ("project_manager", "ProjectManager"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="participants")
    participant_type = models.CharField(max_length=32, choices=PARTICIPANT_TYPE_CHOICES)
    name = models.CharField(max_length=100)
    organization = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    speaker_label = models.CharField(max_length=32, blank=True)
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class CustomerDemandSegment(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("asr_ready", "AsrReady"),
        ("normalized", "Normalized"),
        ("review_required", "ReviewRequired"),
        ("discarded", "Discarded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="segments")
    sequence_no = models.PositiveIntegerField()
    speaker_label = models.CharField(max_length=32, blank=True)
    raw_text = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    final_text = models.TextField(blank=True)
    asr_provider = models.CharField(max_length=50, blank=True)
    llm_provider = models.CharField(max_length=50, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    semantic_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    semantic_payload = models.JSONField(default=dict, blank=True)
    review_flag = models.BooleanField(default=False)
    issues_json = models.JSONField(default=list, blank=True)
    raw_start_ms = models.BigIntegerField(null=True, blank=True)
    raw_end_ms = models.BigIntegerField(null=True, blank=True)
    segment_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence_no", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["session", "sequence_no"], name="uniq_customer_demand_segment_seq"),
        ]
        indexes = [
            models.Index(fields=["session", "sequence_no"]),
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["review_flag"]),
        ]


class CustomerDemandStageSummary(models.Model):
    TRIGGER_TYPE_CHOICES = [
        ("auto_interval", "AutoInterval"),
        ("auto_segment_threshold", "AutoSegmentThreshold"),
        ("manual", "Manual"),
        ("session_end", "SessionEnd"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="stage_summaries")
    summary_version = models.PositiveIntegerField()
    trigger_type = models.CharField(max_length=32, choices=TRIGGER_TYPE_CHOICES, default="manual")
    covered_segment_start = models.PositiveIntegerField(default=1)
    covered_segment_end = models.PositiveIntegerField(default=1)
    summary_markdown = models.TextField(blank=True)
    summary_payload = models.JSONField(default=dict, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_customer_demand_stage_summaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-summary_version", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["session", "summary_version"], name="uniq_customer_demand_summary_version"),
        ]


class CustomerDemandReport(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("superseded", "Superseded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="reports")
    report_version = models.PositiveIntegerField()
    report_title = models.CharField(max_length=255)
    report_markdown = models.TextField(blank=True)
    report_html = models.TextField(blank=True)
    report_payload = models.JSONField(default=dict, blank=True)
    digging_suggestions_markdown = models.TextField(blank=True)
    digging_suggestions_payload = models.JSONField(default=dict, blank=True)
    recommended_questions_markdown = models.TextField(blank=True)
    knowledge_enabled = models.BooleanField(default=False)
    used_knowledge_sources = models.JSONField(default=list, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_customer_demand_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_version", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["session", "report_version"], name="uniq_customer_demand_report_version"),
        ]


class CustomerDemandAnalysisTask(models.Model):
    TASK_TYPE_CHOICES = [
        ("stage_summary", "StageSummary"),
        ("final_analysis", "FinalAnalysis"),
        ("export_report", "ExportReport"),
    ]
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="analysis_tasks")
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="queued")
    current_step = models.CharField(max_length=100, blank=True)
    current_step_label = models.CharField(max_length=100, blank=True)
    progress = models.PositiveIntegerField(default=0)
    request_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="started_customer_demand_tasks",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class CustomerDemandAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CustomerDemandSession, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, blank=True)
    storage_path = models.CharField(max_length=500)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_customer_demand_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
