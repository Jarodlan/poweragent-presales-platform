from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .models import User


LOCK_THRESHOLD = 5
LOCK_MINUTES = 30


def record_login_success(user: User, ip_address: str | None = None) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.account_status = "active"
    if ip_address:
        user.last_login_ip = ip_address
    user.save(update_fields=["failed_login_attempts", "locked_until", "account_status", "last_login_ip"])


def record_login_failure(user: User) -> None:
    user.failed_login_attempts += 1
    update_fields = ["failed_login_attempts"]
    if user.failed_login_attempts >= LOCK_THRESHOLD:
        user.account_status = "locked"
        user.locked_until = timezone.now() + timedelta(minutes=LOCK_MINUTES)
        update_fields.extend(["account_status", "locked_until"])
    user.save(update_fields=update_fields)


def resolve_visible_conversations(user: User) -> QuerySet:
    from apps.conversations.models import Conversation

    if not user.is_authenticated:
        return Conversation.objects.none()
    if user.is_superuser:
        return Conversation.objects.all()
    return Conversation.objects.filter(user=user)


def resolve_visible_tasks(user: User) -> QuerySet:
    from apps.tasks.models import Task

    if not user.is_authenticated:
        return Task.objects.none()
    qs = Task.objects.select_related("conversation", "assistant_message")
    if user.is_superuser:
        return qs
    return qs.filter(conversation__user=user)
