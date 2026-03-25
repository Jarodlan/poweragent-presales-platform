from django.contrib import admin

from .models import FeishuDeliveryRecord, FeishuSyncJob, FeishuTaskRecord, PresalesArchiveRecord, PresalesFollowupReminder, PresalesTask, PresalesTaskActivity


@admin.register(PresalesTask)
class PresalesTaskAdmin(admin.ModelAdmin):
    list_display = ("task_title", "task_type", "customer_name", "assignee_user", "status", "priority", "updated_at")
    search_fields = ("task_title", "customer_name", "source_id")
    list_filter = ("task_type", "status", "priority", "feishu_delivery_status")


@admin.register(PresalesTaskActivity)
class PresalesTaskActivityAdmin(admin.ModelAdmin):
    list_display = ("task", "activity_type", "operator_user", "created_at")
    list_filter = ("activity_type",)


@admin.register(PresalesArchiveRecord)
class PresalesArchiveRecordAdmin(admin.ModelAdmin):
    list_display = ("source_title", "archive_type", "customer_name", "storage_provider", "archive_status", "created_at")
    list_filter = ("archive_type", "archive_status", "storage_provider")


@admin.register(PresalesFollowupReminder)
class PresalesFollowupReminderAdmin(admin.ModelAdmin):
    list_display = ("task", "reminder_type", "target_user", "scheduled_at", "status")
    list_filter = ("reminder_type", "status", "channel")


@admin.register(FeishuDeliveryRecord)
class FeishuDeliveryRecordAdmin(admin.ModelAdmin):
    list_display = ("business_type", "target_type", "target_id", "delivery_status", "created_at")
    list_filter = ("business_type", "target_type", "delivery_status")


@admin.register(FeishuSyncJob)
class FeishuSyncJobAdmin(admin.ModelAdmin):
    list_display = ("job_type", "trigger_type", "status", "created_at", "finished_at")
    list_filter = ("job_type", "trigger_type", "status")


@admin.register(FeishuTaskRecord)
class FeishuTaskRecordAdmin(admin.ModelAdmin):
    list_display = ("presales_task", "operator_name", "operator_identity_key", "feishu_task_id", "status", "created_at")
    list_filter = ("status",)
