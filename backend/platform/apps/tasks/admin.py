from django.contrib import admin

from .models import Task, TaskEvent


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "status", "current_step", "created_at")
    search_fields = ("run_id", "error_message")


@admin.register(TaskEvent)
class TaskEventAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "event_type", "created_at")
