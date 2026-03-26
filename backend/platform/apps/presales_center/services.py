from __future__ import annotations

import threading
from datetime import datetime, timedelta
from urllib.parse import quote
from typing import Iterable

from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.db import close_old_connections
from django.http import Http404
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Department, User
from apps.audit.models import AuditLog
from apps.customer_demand.models import CustomerDemandReport

from .feishu import FeishuApiError, FeishuClient
from .models import FeishuDeliveryRecord, FeishuTaskRecord, PresalesArchiveRecord, PresalesTask, PresalesTaskActivity


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


def _normalize_activity_payload(values: dict | None) -> dict:
    if not values:
        return {}
    normalized: dict = {}
    for key, value in values.items():
        if isinstance(value, User):
            normalized[key] = value.id
        elif isinstance(value, Department):
            normalized[key] = value.id
        elif isinstance(value, datetime):
            normalized[key] = value.isoformat()
        elif isinstance(value, list):
            normalized[key] = [
                item.id if isinstance(item, (User, Department)) else item.isoformat() if isinstance(item, datetime) else item
                for item in value
            ]
        else:
            normalized[key] = value
    return normalized


def _resolve_task_type_label(value: str) -> str:
    return {
        "follow_up": "跟进任务",
        "proposal_review": "方案评审",
        "customer_revisit": "客户回访",
        "internal_alignment": "内部对齐",
        "materials_prepare": "材料准备",
        "manual": "手工任务",
    }.get(value, value)


def _resolve_priority_label(value: str) -> str:
    return {
        "low": "低优先级",
        "medium": "中优先级",
        "high": "高优先级",
        "urgent": "紧急",
    }.get(value, value)


def _resolve_status_label(value: str) -> str:
    return {
        "pending": "待处理",
        "in_progress": "进行中",
        "completed": "已完成",
        "cancelled": "已取消",
        "archived": "已归档",
    }.get(value, value)


def _resolve_source_type_label(value: str) -> str:
    return {
        "manual": "手工创建",
        "customer_demand_report": "需求分析报告",
        "solution_result": "解决方案结果",
    }.get(value, value)


def _format_dt(value) -> str:
    if not value:
        return "未设置"
    local_value = timezone.localtime(value) if timezone.is_aware(value) else value
    return local_value.strftime("%Y-%m-%d %H:%M")


def build_presales_task_text(task: PresalesTask, *, extra_note: str = "") -> str:
    lines = [
        f"售前任务：{task.task_title}",
        f"任务类型：{_resolve_task_type_label(task.task_type)}",
        f"当前状态：{_resolve_status_label(task.status)}",
        f"优先级：{_resolve_priority_label(task.priority)}",
        f"客户名称：{task.customer_name or '未填写'}",
        f"负责人：{task.owner_user.display_name if task.owner_user else '未分配'}",
        f"所属部门：{task.owner_department.name if task.owner_department else '未设置'}",
        f"到期时间：{_format_dt(task.due_at)}",
        f"回访时间：{_format_dt(task.next_follow_up_at)}",
        f"来源：{_resolve_source_type_label(task.source_type)}",
    ]
    if task.task_description:
        lines.append(f"任务说明：{task.task_description}")
    if extra_note:
        lines.append(f"附加说明：{extra_note}")
    return "\n".join(lines)


def build_presales_task_card_payload(task: PresalesTask, *, extra_note: str = "") -> dict:
    task_url = f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/presales?task={quote(str(task.id))}"
    fields = [
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**客户名称**\n{task.customer_name or '未填写'}"},
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**优先级**\n{_resolve_priority_label(task.priority)}"},
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**当前状态**\n{_resolve_status_label(task.status)}"},
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**任务类型**\n{_resolve_task_type_label(task.task_type)}"},
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**到期时间**\n{_format_dt(task.due_at)}"},
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**回访时间**\n{_format_dt(task.next_follow_up_at)}"},
        },
    ]
    elements: list[dict] = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{task.task_title}**"},
        },
        {"tag": "div", "fields": fields},
    ]
    if task.task_description:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**任务说明**\n{task.task_description}"},
            }
        )
    if extra_note:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**附加说明**\n{extra_note}"},
            }
        )
    elements.extend(
        [
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"负责人：{task.owner_user.display_name if task.owner_user else '未分配'}"},
                    {"tag": "plain_text", "content": f"所属部门：{task.owner_department.name if task.owner_department else '未设置'}"},
                    {"tag": "plain_text", "content": f"来源：{_resolve_source_type_label(task.source_type)}"},
                ],
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "转为我的飞书任务"},
                        "type": "primary",
                        "value": {
                            "action": "create_personal_feishu_task",
                            "presales_task_id": str(task.id),
                        },
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开售前闭环中心"},
                        "type": "default",
                        "url": task_url,
                    }
                ],
            },
        ]
    )
    return {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {
            "title": {"tag": "plain_text", "content": "售前任务提醒"},
            "template": "blue",
        },
        "elements": elements,
    }


def build_presales_task_created_card_payload(task: PresalesTask, *, feishu_task_url: str = "", operator_name: str = "") -> dict:
    task_url = f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/presales?task={quote(str(task.id))}"
    header_title = "已创建飞书任务"
    if operator_name:
        header_title = f"{operator_name} 已创建飞书任务"
    elements: list[dict] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{task.task_title}**\n已成功转为飞书任务，请在飞书客户端的任务/待办中继续跟进。",
            },
        },
        {
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": f"客户：{task.customer_name or '未填写'}"},
                {"tag": "plain_text", "content": f"优先级：{_resolve_priority_label(task.priority)}"},
                {"tag": "plain_text", "content": f"到期：{_format_dt(task.due_at)}"},
            ],
        },
        {"tag": "hr"},
    ]
    actions = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "打开我的飞书任务"},
            "type": "primary",
            "url": feishu_task_url or task_url,
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "打开售前闭环中心"},
            "type": "default",
            "url": task_url,
        },
    ]
    elements.append({"tag": "action", "actions": actions})
    return {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_title},
            "template": "green",
        },
        "elements": elements,
    }


def build_feishu_card_toast_payload(*, type_: str, content: str) -> dict:
    return {"toast": {"type": type_, "content": content}}


def build_feishu_card_success_payload(*, presales_task: PresalesTask, record: FeishuTaskRecord, operator_name: str, created: bool) -> dict:
    feishu_task_url = str(((record.response_payload or {}).get("data") or {}).get("task", {}).get("url") or "").strip()
    content = "已成功转为你的飞书任务。"
    if not created:
        content = "你已创建过该飞书任务，无需重复操作。"
    return {
        "toast": {
            "type": "success" if created else "info",
            "content": content,
        },
        "card": {
            "type": "raw",
            "data": build_presales_task_created_card_payload(
                presales_task,
                feishu_task_url=feishu_task_url,
                operator_name=operator_name,
            ),
        },
    }


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
        payload_json=_normalize_activity_payload(validated_updates),
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


def _resolve_identity_key(*, operator_open_id: str = "", operator_user_id: str = "") -> str:
    if operator_open_id:
        return f"open_id:{operator_open_id}"
    if operator_user_id:
        return f"user_id:{operator_user_id}"
    raise FeishuApiError("飞书卡片回调缺少可识别的操作人身份。")


def _resolve_task_due_timestamp(task: PresalesTask) -> int | None:
    value = task.next_follow_up_at or task.due_at
    if not value:
        return None
    local_value = timezone.localtime(value) if timezone.is_aware(value) else value
    # Feishu task API expects a millisecond timestamp string. Using seconds
    # produces a 1970-era due date in the client.
    return int(local_value.timestamp() * 1000)


def _store_feishu_user_auth(user: User, payload: dict) -> User:
    data = payload.get("data") or {}
    expires_in = int(data.get("expires_in") or 7200)
    refresh_expires_in = int(data.get("refresh_expires_in") or 0)
    user.feishu_user_access_token = str(data.get("access_token") or "").strip()
    user.feishu_user_refresh_token = str(data.get("refresh_token") or "").strip()
    user.feishu_user_token_expires_at = timezone.now() + timedelta(seconds=max(expires_in - 120, 60))
    user.feishu_user_refresh_expires_at = (
        timezone.now() + timedelta(seconds=refresh_expires_in)
        if refresh_expires_in
        else None
    )
    user.feishu_personal_task_auth_status = "authorized"
    user.feishu_personal_task_authorized_at = timezone.now()
    user.feishu_open_id = str(data.get("open_id") or user.feishu_open_id or "").strip() or None
    user.feishu_user_id = str(data.get("user_id") or user.feishu_user_id or "").strip() or None
    if data.get("union_id"):
        user.feishu_union_id = str(data.get("union_id") or "").strip()
    user.save(
        update_fields=[
            "feishu_user_access_token",
            "feishu_user_refresh_token",
            "feishu_user_token_expires_at",
            "feishu_user_refresh_expires_at",
            "feishu_personal_task_auth_status",
            "feishu_personal_task_authorized_at",
            "feishu_open_id",
            "feishu_user_id",
            "feishu_union_id",
        ]
    )
    return user


def bind_feishu_user_authorization(*, user: User, code: str) -> User:
    client = FeishuClient()
    payload = client.exchange_user_access_token(code=code)
    data = payload.get("data") or {}
    open_id = str(data.get("open_id") or "").strip()
    user_id = str(data.get("user_id") or "").strip()
    if user.feishu_open_id and open_id and user.feishu_open_id != open_id:
        raise FeishuApiError("当前飞书授权账号与平台已绑定飞书账号不一致，请先核对账号合并关系。")
    if user.feishu_user_id and user_id and user.feishu_user_id != user_id:
        raise FeishuApiError("当前飞书授权账号与平台已绑定飞书用户不一致，请先核对账号合并关系。")
    return _store_feishu_user_auth(user, payload)


def get_valid_feishu_user_access_token(user: User) -> str:
    if user.feishu_personal_task_auth_status != "authorized":
        raise FeishuApiError("当前飞书账号尚未完成个人授权，请先在平台完成“飞书个人任务授权”。")
    if user.feishu_user_access_token and user.feishu_user_token_expires_at and user.feishu_user_token_expires_at > timezone.now():
        return user.feishu_user_access_token
    if not user.feishu_user_refresh_token:
        user.feishu_personal_task_auth_status = "expired"
        user.save(update_fields=["feishu_personal_task_auth_status"])
        raise FeishuApiError("飞书个人任务授权已过期，请重新完成飞书授权。")
    client = FeishuClient()
    payload = client.refresh_user_access_token(refresh_token=user.feishu_user_refresh_token)
    _store_feishu_user_auth(user, payload)
    return user.feishu_user_access_token


def build_feishu_personal_task_payload(task: PresalesTask, *, operator_name: str = "") -> dict:
    task_url = f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/presales?task={quote(str(task.id))}"
    title = f"【售前跟进】{task.task_title}"
    description = build_presales_task_text(task)
    if operator_name:
        description = f"{description}\n领取人：{operator_name}"
    return {
        "title": title,
        "description": description,
        "due_timestamp": _resolve_task_due_timestamp(task),
        "href_url": task_url,
    }


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


@transaction.atomic
def create_personal_feishu_task_for_presales(
    *,
    presales_task: PresalesTask,
    operator_open_id: str = "",
    operator_user_id: str = "",
    operator_name: str = "",
    source_message_id: str = "",
):
    identity_key = _resolve_identity_key(operator_open_id=operator_open_id, operator_user_id=operator_user_id)
    operator_local_user = None
    if operator_open_id:
        operator_local_user = User.objects.filter(feishu_open_id=operator_open_id).first()
    if not operator_local_user and operator_user_id:
        operator_local_user = User.objects.filter(feishu_user_id=operator_user_id).first()
    existing = (
        FeishuTaskRecord.objects.select_for_update()
        .filter(presales_task=presales_task, operator_identity_key=identity_key)
        .first()
    )
    if existing and existing.feishu_task_id:
        return existing, False

    client = FeishuClient()
    user_id_type = "open_id" if operator_open_id else "user_id"
    operator_id = operator_open_id or operator_user_id
    if not operator_local_user:
        raise FeishuApiError("当前飞书操作人尚未与平台账号建立关联，请先完成账号合并。")
    user_access_token = get_valid_feishu_user_access_token(operator_local_user)
    payload = build_feishu_personal_task_payload(presales_task, operator_name=operator_name)
    source_delivery = None
    if source_message_id:
        source_delivery = (
            FeishuDeliveryRecord.objects.filter(
                business_type="presales_task_notification",
                business_id=str(presales_task.id),
                response_payload__data__message_id=source_message_id,
            )
            .order_by("-created_at")
            .first()
        )
    request_payload = {
        "summary": payload["title"],
        "description": payload["description"],
        "due_timestamp": payload["due_timestamp"],
        "source_message_id": source_message_id,
        "operator_open_id": operator_open_id,
        "operator_user_id": operator_user_id,
    }

    record = existing or FeishuTaskRecord(
        presales_task=presales_task,
        source_delivery=source_delivery,
        operator_identity_key=identity_key,
        operator_open_id=operator_open_id,
        operator_user_id=operator_user_id,
        operator_name=operator_name,
    )
    if source_delivery and record.source_delivery_id != source_delivery.id:
        record.source_delivery = source_delivery
    record.request_payload = request_payload
    record.error_code = ""
    record.error_message = ""
    try:
        response_payload = client.create_task(
            user_id_type=user_id_type,
            title=payload["title"],
            description=payload["description"],
            due_timestamp=payload["due_timestamp"],
            href_url=payload["href_url"],
            access_token=user_access_token,
        )
        task_data = (response_payload.get("data") or {}).get("task") or {}
        record.feishu_task_id = str(task_data.get("task_id") or task_data.get("guid") or task_data.get("id") or "")
        raw_task_id = str(task_data.get("task_id") or task_data.get("guid") or task_data.get("id") or "").strip()
        if raw_task_id and operator_id:
            collaborator_added = False
            follower_added = False
            for target_task_id in [raw_task_id, record.feishu_task_id]:
                if not target_task_id:
                    continue
                if not collaborator_added:
                    try:
                        client.create_task_collaborator(
                            task_id=target_task_id,
                            user_id_type=user_id_type,
                            collaborator_id=operator_id,
                        )
                        collaborator_added = True
                    except Exception:
                        pass
                if not follower_added:
                    try:
                        client.create_task_follower(
                            task_id=target_task_id,
                            user_id_type=user_id_type,
                            follower_id=operator_id,
                        )
                        follower_added = True
                    except Exception:
                        pass
        record.status = "created"
        record.response_payload = response_payload
        record.save()
        _create_task_activity(
            presales_task,
            activity_type="feishu_task_created",
            operator_user=operator_local_user or presales_task.owner_user,
            summary=f"飞书用户 {operator_name or operator_id} 已创建个人任务",
            payload_json={
                "operator_open_id": operator_open_id,
                "operator_user_id": operator_user_id,
                "feishu_task_id": record.feishu_task_id,
            },
        )
        return record, True
    except Exception as exc:  # noqa: BLE001
        response_payload = exc.response_payload if isinstance(exc, FeishuApiError) else {}
        record.status = "failed"
        record.response_payload = response_payload
        record.error_code = str(exc.code) if isinstance(exc, FeishuApiError) and exc.code is not None else ""
        record.error_message = str(exc)
        record.save()
        raise


def _async_create_personal_feishu_task_for_card_action(
    *,
    presales_task: PresalesTask,
    operator_open_id: str,
    operator_user_id: str,
    operator_name: str,
    source_message_id: str,
    callback_token: str,
) -> None:
    close_old_connections()
    try:
        record, _created = create_personal_feishu_task_for_presales(
            presales_task=presales_task,
            operator_open_id=operator_open_id,
            operator_user_id=operator_user_id,
            operator_name=operator_name,
            source_message_id=source_message_id,
        )
        if callback_token:
            feishu_task_url = str(((record.response_payload or {}).get("data") or {}).get("task", {}).get("url") or "").strip()
            FeishuClient().update_card_by_token(
                token=callback_token,
                card=build_presales_task_created_card_payload(
                    presales_task,
                    feishu_task_url=feishu_task_url,
                    operator_name=operator_name,
                ),
                open_ids=[operator_open_id] if operator_open_id else None,
            )
    except Exception as exc:  # noqa: BLE001
        if callback_token:
            try:
                failure_card = build_presales_task_card_payload(
                    presales_task,
                    extra_note=f"转为飞书任务失败：{exc}",
                )
                FeishuClient().update_card_by_token(
                    token=callback_token,
                    card=failure_card,
                    open_ids=[operator_open_id] if operator_open_id else None,
                )
            except Exception:
                pass
    finally:
        close_old_connections()


def handle_feishu_personal_task_card_action(
    *,
    task_id: str,
    operator_open_id: str = "",
    operator_user_id: str = "",
    operator_name: str = "",
    callback_token: str = "",
    source_message_id: str = "",
) -> dict:
    if not task_id:
        return build_feishu_card_toast_payload(type_="danger", content="缺少售前任务标识，无法创建飞书任务。")

    try:
        presales_task = PresalesTask.objects.get(id=task_id)
    except PresalesTask.DoesNotExist:
        return build_feishu_card_toast_payload(type_="danger", content="售前任务不存在或已被删除。")

    try:
        identity_key = _resolve_identity_key(operator_open_id=operator_open_id, operator_user_id=operator_user_id)
    except FeishuApiError as exc:
        return build_feishu_card_toast_payload(type_="danger", content=str(exc))

    existing = (
        FeishuTaskRecord.objects.filter(
            presales_task=presales_task,
            operator_identity_key=identity_key,
        )
        .order_by("-created_at")
        .first()
    )

    if existing and existing.feishu_task_id:
        return build_feishu_card_success_payload(
            presales_task=presales_task,
            record=existing,
            operator_name=operator_name,
            created=False,
        )

    if existing and existing.status == "pending":
        return build_feishu_card_toast_payload(type_="info", content="正在为你创建飞书任务，请稍候。")

    pending_record = existing or FeishuTaskRecord(
        presales_task=presales_task,
        operator_identity_key=identity_key,
        operator_open_id=operator_open_id,
        operator_user_id=operator_user_id,
        operator_name=operator_name,
        status="pending",
    )
    pending_record.status = "pending"
    pending_record.error_code = ""
    pending_record.error_message = ""
    pending_record.save()

    threading.Thread(
        target=_async_create_personal_feishu_task_for_card_action,
        kwargs={
            "presales_task": presales_task,
            "operator_open_id": operator_open_id,
            "operator_user_id": operator_user_id,
            "operator_name": operator_name,
            "source_message_id": source_message_id,
            "callback_token": callback_token,
        },
        daemon=True,
    ).start()
    return build_feishu_card_toast_payload(type_="info", content="正在为你创建飞书任务，请稍候。")


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
    allowlist = set(settings.FEISHU_SYNC_DEPARTMENT_ALLOWLIST or [])
    if allowlist:
        items = [
            item
            for item in items
            if (item.get("open_department_id") or item.get("department_id")) in allowlist
        ]
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
    synced_users: set[str] = set()
    disabled_count = 0
    departments = list(Department.objects.exclude(feishu_department_id__isnull=True))

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
                synced_users.add(feishu_user_id)
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

    job.synced_user_count = len(synced_users)
    job.disabled_user_count = disabled_count
    return len(synced_users), disabled_count


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
