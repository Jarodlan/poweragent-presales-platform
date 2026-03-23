from __future__ import annotations

from typing import Iterable

from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Department, User
from apps.audit.models import AuditLog
from apps.customer_demand.models import CustomerDemandReport

from .feishu import FeishuApiError, FeishuClient
from .models import FeishuDeliveryRecord, PresalesArchiveRecord, PresalesTask, PresalesTaskActivity


def resolve_visible_presales_tasks(user: User):
    qs = PresalesTask.objects.select_related(
        "owner_user",
        "owner_department",
        "assignee_user",
        "created_by",
        "latest_feishu_delivery",
    )
    if user.is_superuser or user.has_permission_code("presales_task.manage"):
        return qs
    return qs.filter(Q(owner_user=user) | Q(assignee_user=user)).distinct()


def resolve_visible_presales_archives(user: User):
    qs = PresalesArchiveRecord.objects.select_related("uploaded_by")
    if user.is_superuser or user.has_permission_code("presales_archive.manage"):
        return qs
    return qs.filter(uploaded_by=user)


def _log_audit(user, action: str, resource_type: str, resource_id: str, detail_json: dict | None = None):
    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=detail_json or {},
    )


def _create_task_activity(task: PresalesTask, *, activity_type: str, operator_user, summary: str, from_status: str = "", to_status: str = "", details_markdown: str = "", payload_json: dict | None = None):
    return PresalesTaskActivity.objects.create(
        task=task,
        activity_type=activity_type,
        operator_user=operator_user,
        from_status=from_status,
        to_status=to_status,
        summary=summary,
        details_markdown=details_markdown,
        payload_json=payload_json or {},
    )


def _normalize_collaborators(values: Iterable[int] | None) -> list[int]:
    if not values:
        return []
    return sorted({int(item) for item in values})


@transaction.atomic
def create_presales_task(*, created_by, owner_user=None, owner_department=None, assignee_user=None, task_title: str, task_type: str = "follow_up", task_description: str = "", source_type: str = "manual", source_id: str = "", source_version: int | None = None, customer_name: str = "", customer_id: str = "", priority: str = "medium", due_at=None, next_follow_up_at=None, collaborator_user_ids=None, payload_json: dict | None = None):
    task = PresalesTask.objects.create(
        task_title=task_title,
        task_type=task_type,
        task_description=task_description,
        source_type=source_type,
        source_id=source_id,
        source_version=source_version,
        customer_name=customer_name,
        customer_id=customer_id,
        owner_user=owner_user or created_by,
        owner_department=owner_department or getattr(created_by, "department", None),
        assignee_user=assignee_user,
        collaborator_user_ids=_normalize_collaborators(collaborator_user_ids),
        priority=priority,
        due_at=due_at,
        next_follow_up_at=next_follow_up_at,
        followup_status="scheduled" if next_follow_up_at else "not_scheduled",
        payload_json=payload_json or {},
        created_by=created_by,
    )
    _create_task_activity(
        task,
        activity_type="created",
        operator_user=created_by,
        summary=f"创建任务：{task.task_title}",
        to_status=task.status,
        payload_json={"source_type": task.source_type, "source_id": task.source_id},
    )
    _log_audit(created_by, "presales_task.create", "presales_task", str(task.id), {"task_title": task.task_title})
    return task


@transaction.atomic
def create_task_from_demand_report(*, report: CustomerDemandReport, created_by, assignee_user=None, task_title: str, task_description: str = "", priority: str = "medium", due_at=None, next_follow_up_at=None, collaborator_user_ids=None, payload_json: dict | None = None):
    payload = dict(payload_json or {})
    payload.setdefault("report_title", report.report_title)
    payload.setdefault("session_id", str(report.session_id))
    task = create_presales_task(
        created_by=created_by,
        owner_user=report.session.owner,
        owner_department=report.session.department,
        assignee_user=assignee_user,
        task_title=task_title,
        task_type="follow_up",
        task_description=task_description,
        source_type="customer_demand_report",
        source_id=str(report.id),
        source_version=report.report_version,
        customer_name=report.session.customer_name,
        priority=priority,
        due_at=due_at,
        next_follow_up_at=next_follow_up_at,
        collaborator_user_ids=collaborator_user_ids,
        payload_json=payload,
    )
    return task


@transaction.atomic
def create_task_from_solution_result(*, created_by, source_id: str, source_title: str, customer_name: str = "", assignee_user=None, task_title: str, task_description: str = "", priority: str = "medium", due_at=None, next_follow_up_at=None, collaborator_user_ids=None, payload_json: dict | None = None):
    payload = dict(payload_json or {})
    payload.setdefault("solution_title", source_title)
    task = create_presales_task(
        created_by=created_by,
        owner_user=created_by,
        owner_department=getattr(created_by, "department", None),
        assignee_user=assignee_user,
        task_title=task_title,
        task_type="proposal_review",
        task_description=task_description,
        source_type="solution_result",
        source_id=source_id,
        customer_name=customer_name,
        priority=priority,
        due_at=due_at,
        next_follow_up_at=next_follow_up_at,
        collaborator_user_ids=collaborator_user_ids,
        payload_json=payload,
    )
    return task


@transaction.atomic
def update_presales_task(task: PresalesTask, *, operator_user, validated_updates: dict):
    old_status = task.status
    status_changed = False
    for attr, value in validated_updates.items():
        setattr(task, attr, value)
        if attr == "status" and value != old_status:
            status_changed = True
    task.followup_status = "scheduled" if task.next_follow_up_at and task.status not in {"completed", "cancelled"} else task.followup_status
    task.save()
    activity_type = "status_changed" if status_changed else "updated"
    _create_task_activity(
        task,
        activity_type=activity_type,
        operator_user=operator_user,
        summary=f"更新任务：{task.task_title}",
        from_status=old_status,
        to_status=task.status,
        payload_json=validated_updates,
    )
    _log_audit(operator_user, "presales_task.update", "presales_task", str(task.id), {"fields": sorted(validated_updates.keys())})
    return task


@transaction.atomic
def complete_presales_task(task: PresalesTask, *, operator_user, summary: str = ""):
    old_status = task.status
    task.status = "completed"
    task.followup_status = "done" if task.next_follow_up_at else task.followup_status
    task.save(update_fields=["status", "followup_status", "updated_at"])
    _create_task_activity(
        task,
        activity_type="closed",
        operator_user=operator_user,
        summary=summary or f"完成任务：{task.task_title}",
        from_status=old_status,
        to_status=task.status,
        payload_json={"completed_at": timezone.now().isoformat()},
    )
    _log_audit(operator_user, "presales_task.complete", "presales_task", str(task.id), {"summary": summary})
    return task


@transaction.atomic
def queue_feishu_delivery(*, operator_user, business_type: str, business_id: str, target_type: str, target_id: str, target_name: str = "", message_type: str = "text", request_payload: dict | None = None):
    delivery = FeishuDeliveryRecord.objects.create(
        business_type=business_type,
        business_id=business_id,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        message_type=message_type,
        request_payload=request_payload or {},
        delivery_status="queued",
        operator_user=operator_user,
    )
    _log_audit(operator_user, "feishu_delivery.queue", "feishu_delivery", str(delivery.id), {"business_type": business_type, "target_type": target_type})
    return delivery


def _resolve_receive_id_type(target_type: str, target_id: str) -> str:
    if target_type == "group":
        return "chat_id"
    if target_type == "user":
        return "open_id" if target_id.startswith("ou_") else "user_id"
    raise FeishuApiError(f"暂不支持的飞书目标类型：{target_type}")


@transaction.atomic
def deliver_feishu_record(delivery: FeishuDeliveryRecord, *, operator_user=None) -> FeishuDeliveryRecord:
    client = FeishuClient()
    delivery.delivery_status = "queued"
    delivery.error_code = ""
    delivery.error_message = ""
    delivery.save(update_fields=["delivery_status", "error_code", "error_message", "updated_at"])
    try:
        receive_id_type = _resolve_receive_id_type(delivery.target_type, delivery.target_id)
        response_payload = client.send_message(
            receive_id=delivery.target_id,
            receive_id_type=receive_id_type,
            message_type=delivery.message_type,
            message_payload=delivery.request_payload or {},
        )
        delivery.response_payload = response_payload
        delivery.delivery_status = "sent"
        delivery.error_code = ""
        delivery.error_message = ""
        delivery.operator_user = operator_user or delivery.operator_user
        delivery.save(update_fields=["response_payload", "delivery_status", "error_code", "error_message", "operator_user", "updated_at"])
        _log_audit(
            operator_user or delivery.operator_user,
            "feishu_delivery.sent",
            "feishu_delivery",
            str(delivery.id),
            {"target_type": delivery.target_type, "target_id": delivery.target_id},
        )
        return delivery
    except Exception as exc:  # noqa: BLE001
        payload = exc.response_payload if isinstance(exc, FeishuApiError) else {}
        delivery.response_payload = payload
        delivery.delivery_status = "failed"
        delivery.retry_count = delivery.retry_count + 1
        delivery.error_code = str(exc.code) if isinstance(exc, FeishuApiError) and exc.code is not None else ""
        delivery.error_message = str(exc)
        delivery.operator_user = operator_user or delivery.operator_user
        delivery.save(
            update_fields=[
                "response_payload",
                "delivery_status",
                "retry_count",
                "error_code",
                "error_message",
                "operator_user",
                "updated_at",
            ]
        )
        _log_audit(
            operator_user or delivery.operator_user,
            "feishu_delivery.failed",
            "feishu_delivery",
            str(delivery.id),
            {"target_type": delivery.target_type, "target_id": delivery.target_id, "error": str(exc)},
        )
        raise


def _build_department_tree(client: FeishuClient) -> list[dict]:
    queue: list[str] = ["0"]
    collected: list[dict] = []
    visited: set[str] = set()
    while queue:
        parent_id = queue.pop(0)
        page_token: str | None = None
        while True:
            payload = client.list_department_children(department_id=parent_id, page_token=page_token)
            data = payload.get("data") or {}
            items = data.get("items") or []
            for item in items:
                department_id = item.get("open_department_id") or item.get("department_id")
                if not department_id or department_id in visited:
                    continue
                visited.add(department_id)
                collected.append(item)
                queue.append(department_id)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
    return collected


def _sync_departments(job, *, operator_user=None) -> int:
    client = FeishuClient()
    items = _build_department_tree(client)
    now = timezone.now()
    existing_by_feishu = {item.feishu_department_id: item for item in Department.objects.exclude(feishu_department_id__isnull=True)}
    created_or_updated = 0
    resolved: dict[str, Department] = {}
    pending_parent_links: list[tuple[Department, str]] = []

    for item in items:
        feishu_department_id = item.get("open_department_id") or item.get("department_id")
        if not feishu_department_id:
            continue
        defaults = {
            "name": item.get("name") or feishu_department_id,
            "code": existing_by_feishu.get(feishu_department_id).code if existing_by_feishu.get(feishu_department_id) else f"feishu:{feishu_department_id}",
            "status": "active",
            "sync_source": "feishu",
            "last_synced_at": now,
        }
        department = existing_by_feishu.get(feishu_department_id)
        if department:
            department.name = defaults["name"]
            department.status = defaults["status"]
            department.sync_source = "feishu"
            department.last_synced_at = now
            department.save(update_fields=["name", "status", "sync_source", "last_synced_at", "updated_at"])
        else:
            department = Department.objects.create(
                name=defaults["name"],
                code=defaults["code"],
                status="active",
                sync_source="feishu",
                feishu_department_id=feishu_department_id,
                last_synced_at=now,
            )
        created_or_updated += 1
        resolved[feishu_department_id] = department
        parent_id = item.get("parent_open_department_id") or item.get("parent_department_id")
        if parent_id and parent_id != "0":
            pending_parent_links.append((department, parent_id))

    for department, parent_feishu_id in pending_parent_links:
        parent = resolved.get(parent_feishu_id)
        if parent and department.parent_id != parent.id:
            department.parent = parent
            department.save(update_fields=["parent", "updated_at"])

    job.synced_department_count = created_or_updated
    return created_or_updated


def _sync_users(job, *, operator_user=None) -> tuple[int, int]:
    client = FeishuClient()
    now = timezone.now()
    seen_user_ids: set[str] = set()
    synced_count = 0
    disabled_count = 0
    departments = list(Department.objects.filter(sync_source="feishu").exclude(feishu_department_id__isnull=True))

    for department in departments:
        page_token: str | None = None
        while True:
            payload = client.list_department_users(department_id=department.feishu_department_id, page_token=page_token)
            data = payload.get("data") or {}
            items = data.get("items") or []
            for item in items:
                feishu_user_id = item.get("user_id") or item.get("open_id")
                feishu_open_id = item.get("open_id") or ""
                if not feishu_user_id:
                    continue
                seen_user_ids.add(feishu_user_id)
                username = item.get("email") or item.get("mobile") or f"feishu_{feishu_user_id}"
                user = User.objects.filter(feishu_user_id=feishu_user_id).first()
                if not user and feishu_open_id:
                    user = User.objects.filter(feishu_open_id=feishu_open_id).first()
                if not user and item.get("email"):
                    user = User.objects.filter(email=item["email"]).first()
                created = False
                if not user:
                    user = User(
                        username=username[:150],
                        email=item.get("email", ""),
                        is_active=True,
                        account_status="active",
                        sync_source="feishu",
                        sync_status="synced",
                    )
                    user.set_unusable_password()
                    created = True
                user.display_name = item.get("name") or user.display_name or username
                user.email = item.get("email", user.email or "")
                user.phone_number = item.get("mobile", user.phone_number or "")
                user.employee_no = item.get("employee_no", user.employee_no or "")
                user.department = department
                user.account_status = "active"
                user.is_active = True
                user.sync_source = "feishu"
                user.sync_status = "synced"
                user.feishu_user_id = feishu_user_id
                user.feishu_open_id = feishu_open_id or user.feishu_open_id
                user.feishu_union_id = item.get("union_id", user.feishu_union_id or "")
                user.last_synced_at = now
                user.last_external_status = "active"
                if created:
                    user.save()
                else:
                    user.save(
                        update_fields=[
                            "display_name",
                            "email",
                            "phone_number",
                            "employee_no",
                            "department",
                            "account_status",
                            "is_active",
                            "sync_source",
                            "sync_status",
                            "feishu_user_id",
                            "feishu_open_id",
                            "feishu_union_id",
                            "last_synced_at",
                            "last_external_status",
                        ]
                    )
                synced_count += 1
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

    synced_feishu_users = User.objects.filter(sync_source="feishu").exclude(feishu_user_id__isnull=True)
    stale_users = synced_feishu_users.exclude(feishu_user_id__in=seen_user_ids)
    for user in stale_users:
        user.account_status = "inactive"
        user.is_active = False
        user.sync_status = "disabled"
        user.last_external_status = "inactive_or_missing"
        user.last_synced_at = now
        user.save(update_fields=["account_status", "is_active", "sync_status", "last_external_status", "last_synced_at"])
        Token.objects.filter(user=user).delete()
        disabled_count += 1

    job.synced_user_count = synced_count
    job.disabled_user_count = disabled_count
    return synced_count, disabled_count


@transaction.atomic
def run_feishu_sync_job(job, *, operator_user=None):
    job.status = "running"
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message", "updated_at"])
    try:
        summary: dict[str, object] = {}
        if job.job_type in {"sync_departments", "full_sync"}:
            summary["departments"] = _sync_departments(job, operator_user=operator_user)
        if job.job_type in {"sync_users", "full_sync"}:
            synced_count, disabled_count = _sync_users(job, operator_user=operator_user)
            summary["users"] = synced_count
            summary["disabled_users"] = disabled_count
        job.summary_json = summary
        job.status = "completed"
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "synced_user_count",
                "synced_department_count",
                "disabled_user_count",
                "summary_json",
                "status",
                "finished_at",
                "updated_at",
            ]
        )
        _log_audit(operator_user, "feishu_sync.completed", "feishu_sync_job", str(job.id), summary)
        return job
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error_count = job.error_count + 1
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_count", "error_message", "finished_at", "updated_at"])
        _log_audit(operator_user, "feishu_sync.failed", "feishu_sync_job", str(job.id), {"error": str(exc)})
        raise
