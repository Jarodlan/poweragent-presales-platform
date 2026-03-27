from django.contrib import admin

from .models import CrmWritebackRecord


@admin.register(CrmWritebackRecord)
class CrmWritebackRecordAdmin(admin.ModelAdmin):
    list_display = ("object_type", "object_id", "target_table", "action", "status", "created_by", "created_at")
    list_filter = ("provider", "object_type", "target_table", "action", "status")
    search_fields = ("object_id", "target_record_id", "error_message")
    readonly_fields = ("created_at", "updated_at")
