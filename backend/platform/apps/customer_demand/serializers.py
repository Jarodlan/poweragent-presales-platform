from __future__ import annotations

from rest_framework import serializers

from .models import (
    CustomerDemandAnalysisTask,
    CustomerDemandAttachment,
    CustomerDemandParticipant,
    CustomerDemandReport,
    CustomerDemandSegment,
    CustomerDemandSession,
    CustomerDemandStageSummary,
)


class CustomerDemandParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandParticipant
        fields = [
            "id",
            "participant_type",
            "name",
            "organization",
            "job_title",
            "speaker_label",
            "is_internal",
            "created_at",
        ]


class CustomerDemandSessionSerializer(serializers.ModelSerializer):
    owner_display_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    latest_report_id = serializers.SerializerMethodField()

    class Meta:
        model = CustomerDemandSession
        fields = [
            "id",
            "owner",
            "owner_display_name",
            "department",
            "department_name",
            "customer_name",
            "session_title",
            "industry",
            "region",
            "topic",
            "customer_type",
            "knowledge_enabled",
            "knowledge_scope",
            "status",
            "recording_started_at",
            "recording_stopped_at",
            "analysis_started_at",
            "analysis_finished_at",
            "raw_segment_count",
            "normalized_segment_count",
            "latest_stage_version",
            "latest_report_id",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "owner",
            "recording_started_at",
            "recording_stopped_at",
            "analysis_started_at",
            "analysis_finished_at",
            "raw_segment_count",
            "normalized_segment_count",
            "latest_stage_version",
            "latest_report_id",
            "created_at",
            "updated_at",
        ]

    def get_owner_display_name(self, obj):
        return obj.owner.display_name or obj.owner.username

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def get_latest_report_id(self, obj):
        report = obj.reports.order_by("-report_version", "-created_at").first()
        return str(report.id) if report else None


class CustomerDemandSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandSession
        fields = [
            "customer_name",
            "session_title",
            "industry",
            "region",
            "topic",
            "customer_type",
            "knowledge_enabled",
            "knowledge_scope",
            "remarks",
        ]


class CustomerDemandSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandSegment
        fields = [
            "id",
            "session",
            "sequence_no",
            "speaker_label",
            "raw_text",
            "normalized_text",
            "final_text",
            "asr_provider",
            "llm_provider",
            "confidence_score",
            "semantic_score",
            "semantic_payload",
            "review_flag",
            "issues_json",
            "raw_start_ms",
            "raw_end_ms",
            "segment_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CustomerDemandSegmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandSegment
        fields = [
            "sequence_no",
            "speaker_label",
            "raw_text",
            "normalized_text",
            "final_text",
            "asr_provider",
            "llm_provider",
            "confidence_score",
            "semantic_score",
            "semantic_payload",
            "review_flag",
            "issues_json",
            "raw_start_ms",
            "raw_end_ms",
            "segment_status",
        ]


class CustomerDemandStageSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandStageSummary
        fields = [
            "id",
            "session",
            "summary_version",
            "trigger_type",
            "covered_segment_start",
            "covered_segment_end",
            "summary_markdown",
            "summary_payload",
            "llm_model",
            "created_by",
            "created_at",
        ]


class CustomerDemandReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandReport
        fields = [
            "id",
            "session",
            "report_version",
            "report_title",
            "report_markdown",
            "report_html",
            "report_payload",
            "digging_suggestions_markdown",
            "digging_suggestions_payload",
            "recommended_questions_markdown",
            "knowledge_enabled",
            "used_knowledge_sources",
            "llm_model",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]


class CustomerDemandAnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDemandAnalysisTask
        fields = [
            "id",
            "session",
            "task_type",
            "status",
            "current_step",
            "current_step_label",
            "progress",
            "request_payload",
            "result_payload",
            "error_message",
            "started_by",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]


class CustomerDemandRecordingAttachmentSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField()
    mime_type = serializers.SerializerMethodField()

    class Meta:
        model = CustomerDemandAttachment
        fields = [
            "id",
            "session",
            "file_name",
            "file_type",
            "uploaded_by",
            "created_at",
            "file_size",
            "mime_type",
        ]
        read_only_fields = fields

    def get_file_size(self, obj):
        from pathlib import Path

        path = Path(obj.storage_path)
        if not path.exists():
            return 0
        return path.stat().st_size

    def get_mime_type(self, obj):
        file_type = (obj.file_type or "").strip()
        if file_type.startswith("recording:"):
            return file_type.split(":", 1)[1] or "audio/wav"
        return file_type or "audio/wav"
