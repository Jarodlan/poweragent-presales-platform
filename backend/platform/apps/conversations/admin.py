from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "updated_at")
    search_fields = ("title", "last_user_message")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "status", "created_at")
    search_fields = ("query_text", "summary_text")
