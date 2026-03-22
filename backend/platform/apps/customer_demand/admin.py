from django.contrib import admin

from .models import (
    CustomerDemandAnalysisTask,
    CustomerDemandAttachment,
    CustomerDemandParticipant,
    CustomerDemandReport,
    CustomerDemandSegment,
    CustomerDemandSession,
    CustomerDemandStageSummary,
)


@admin.register(CustomerDemandSession)
class CustomerDemandSessionAdmin(admin.ModelAdmin):
    list_display = ("session_title", "customer_name", "owner", "status", "knowledge_enabled", "updated_at")
    search_fields = ("session_title", "customer_name", "topic", "industry", "region")
    list_filter = ("status", "knowledge_enabled", "industry", "region")


@admin.register(CustomerDemandSegment)
class CustomerDemandSegmentAdmin(admin.ModelAdmin):
    list_display = ("session", "sequence_no", "speaker_label", "segment_status", "review_flag", "created_at")
    list_filter = ("segment_status", "review_flag", "asr_provider", "llm_provider")
    search_fields = ("raw_text", "normalized_text", "final_text")


@admin.register(CustomerDemandStageSummary)
class CustomerDemandStageSummaryAdmin(admin.ModelAdmin):
    list_display = ("session", "summary_version", "trigger_type", "created_at")
    list_filter = ("trigger_type",)


@admin.register(CustomerDemandReport)
class CustomerDemandReportAdmin(admin.ModelAdmin):
    list_display = ("session", "report_version", "report_title", "status", "knowledge_enabled", "created_at")
    list_filter = ("status", "knowledge_enabled")
    search_fields = ("report_title", "report_markdown")


@admin.register(CustomerDemandAnalysisTask)
class CustomerDemandAnalysisTaskAdmin(admin.ModelAdmin):
    list_display = ("session", "task_type", "status", "current_step_label", "progress", "created_at")
    list_filter = ("task_type", "status")


@admin.register(CustomerDemandParticipant)
class CustomerDemandParticipantAdmin(admin.ModelAdmin):
    list_display = ("session", "name", "participant_type", "speaker_label", "is_internal")
    list_filter = ("participant_type", "is_internal")


@admin.register(CustomerDemandAttachment)
class CustomerDemandAttachmentAdmin(admin.ModelAdmin):
    list_display = ("session", "file_name", "file_type", "uploaded_by", "created_at")

