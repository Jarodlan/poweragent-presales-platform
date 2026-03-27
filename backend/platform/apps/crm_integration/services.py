from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.conversations.models import Conversation, Message
from apps.customer_demand.models import CustomerDemandReport, CustomerDemandSession
from apps.presales_center.models import PresalesArchiveRecord, PresalesTask
from apps.presales_center.feishu import FeishuApiError, FeishuClient

from .models import CrmWritebackRecord


CRM_PROVIDER = "feishu_bitable"
DEFAULT_FIELD_MAP = {
    "customer": {
        "name": "客户名称",
        "industry": "所属行业",
        "region": "",
        "level": "客户规模",
        "owner_name": "客户所有人",
        "last_followup_at": "最近跟进时间",
    },
    "opportunity": {
        "name": "商机名称",
        "stage": "跟进阶段",
        "owner_name": "跟进销售人员",
        "amount": "业务价值",
        "next_followup_at": "预计交易日期",
        "customer_record_id": "客户名称",
        "customer_name": "客户名称",
    },
    "followup": {
        "customer_record_id": "客户名称",
        "summary": "跟进内容",
        "followup_form": "跟进形式",
        "result_link": "跟进妙记链接",
    },
    "attachment": {
        "customer_record_id": "客户名称",
        "summary": "跟进内容",
        "followup_form": "跟进形式",
        "result_link": "跟进妙记链接",
    },
}


class CrmIntegrationError(RuntimeError):
    pass


class FeishuCrmClient:
    def __init__(self) -> None:
        self.feishu_client = FeishuClient()
        self.app_token = settings.FEISHU_BITABLE_APP_TOKEN

    def ensure_configured(self) -> None:
        if not getattr(settings, "FEISHU_CRM_ENABLED", False):
            raise CrmIntegrationError("飞书 CRM 未开启，请先配置 FEISHU_CRM_ENABLED。")
        if not self.app_token:
            raise CrmIntegrationError("缺少 FEISHU_BITABLE_APP_TOKEN，无法访问飞书 CRM 多维表格。")

    def _table_id(self, table_name: str) -> str:
        mapping = {
            "customer": settings.FEISHU_CRM_CUSTOMER_TABLE_ID,
            "contact": settings.FEISHU_CRM_CONTACT_TABLE_ID,
            "opportunity": settings.FEISHU_CRM_OPPORTUNITY_TABLE_ID,
            "followup": settings.FEISHU_CRM_FOLLOWUP_TABLE_ID,
            "attachment": settings.FEISHU_CRM_ATTACHMENT_TABLE_ID,
        }
        table_id = mapping.get(table_name) or ""
        if not table_id:
            raise CrmIntegrationError(f"飞书 CRM 表 {table_name} 未配置 table_id。")
        return table_id

    def list_records(self, table_name: str, *, page_size: int = 100) -> list[dict[str, Any]]:
        self.ensure_configured()
        table_id = self._table_id(table_name)
        page_token = None
        items: list[dict[str, Any]] = []
        while True:
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            payload = self.feishu_client._request(
                "GET",
                f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records",
                params=params,
            )
            data = payload.get("data") or {}
            items.extend(data.get("items") or [])
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
        return items

    def create_record(self, table_name: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.ensure_configured()
        table_id = self._table_id(table_name)
        payload = self.feishu_client._request(
            "POST",
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records",
            json_body={"fields": fields},
        )
        return payload.get("data") or {}

    def update_record(self, table_name: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.ensure_configured()
        table_id = self._table_id(table_name)
        payload = self.feishu_client._request(
            "PUT",
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}",
            json_body={"fields": fields},
        )
        return payload.get("data") or {}


def _field_value(fields: dict[str, Any], field_name: str) -> Any:
    if not field_name:
        return ""
    return fields.get(field_name, "")


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("name") or item.get("record_id") or item.get("id") or ""))
            else:
                parts.append(str(item))
        return "、".join(part for part in parts if part)
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or value.get("record_id") or value.get("id") or "")
    return str(value)


def _format_feishu_datetime(value: Any) -> str:
    if value in ("", None):
        return ""
    if isinstance(value, (int, float)):
        numeric = float(value)
        # Feishu Bitable may return excel-style serial dates or millisecond timestamps.
        if numeric > 10_000_000_000:
            dt = datetime.fromtimestamp(numeric / 1000, tz=timezone.get_current_timezone())
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        if numeric > 10_000_000:
            dt = datetime.fromtimestamp(numeric, tz=timezone.get_current_timezone())
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        base = datetime(1899, 12, 30, tzinfo=timezone.get_current_timezone())
        dt = base + timedelta(days=numeric)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return _coerce_text(value)


def _extract_linked_ids(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("record_ids"):
                    result.extend(str(record_id) for record_id in item.get("record_ids") or [] if record_id)
                    continue
                record_id = item.get("record_id") or item.get("id") or item.get("text")
                if record_id:
                    result.append(str(record_id))
            else:
                result.append(str(item))
        return [item for item in result if item]
    if isinstance(value, dict):
        record_id = value.get("record_id") or value.get("id") or value.get("text")
        return [str(record_id)] if record_id else []
    return []


def _normalize_customer_record(base_id: str, item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields") or {}
    fmap = DEFAULT_FIELD_MAP["customer"]
    return {
        "provider": CRM_PROVIDER,
        "base_id": base_id,
        "table": "customer",
        "record_id": str(item.get("record_id") or item.get("recordId") or ""),
        "name": _coerce_text(_field_value(fields, fmap["name"])),
        "industry": _coerce_text(_field_value(fields, fmap["industry"])),
        "region": _coerce_text(_field_value(fields, fmap["region"])) if fmap.get("region") else "",
        "level": _coerce_text(_field_value(fields, fmap["level"])),
        "owner_name": _coerce_text(_field_value(fields, fmap["owner_name"])),
        "last_followup_at": _format_feishu_datetime(_field_value(fields, fmap["last_followup_at"])),
    }


def _normalize_opportunity_record(base_id: str, item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields") or {}
    fmap = DEFAULT_FIELD_MAP["opportunity"]
    customer_link_ids = _extract_linked_ids(_field_value(fields, fmap["customer_record_id"]))
    customer_record_id = customer_link_ids[0] if customer_link_ids else _coerce_text(_field_value(fields, fmap["customer_record_id"]))
    return {
        "provider": CRM_PROVIDER,
        "base_id": base_id,
        "table": "opportunity",
        "record_id": str(item.get("record_id") or item.get("recordId") or ""),
        "customer_record_id": customer_record_id,
        "name": _coerce_text(_field_value(fields, fmap["name"])),
        "stage": _coerce_text(_field_value(fields, fmap["stage"])),
        "owner_name": _coerce_text(_field_value(fields, fmap["owner_name"])),
        "amount": _coerce_text(_field_value(fields, fmap["amount"])),
        "next_followup_at": _format_feishu_datetime(_field_value(fields, fmap["next_followup_at"])),
        "customer_name": _coerce_text(_field_value(fields, fmap["customer_name"])),
    }


def search_customer_records(*, keyword: str = "", owner_name: str = "") -> list[dict[str, Any]]:
    client = FeishuCrmClient()
    records = [_normalize_customer_record(client.app_token, item) for item in client.list_records("customer")]
    keyword = keyword.strip().lower()
    owner_name = owner_name.strip().lower()
    result = []
    for record in records:
        haystack = " ".join([record.get("name", ""), record.get("industry", ""), record.get("region", "")]).lower()
        if keyword and keyword not in haystack:
            continue
        if owner_name and owner_name not in (record.get("owner_name") or "").lower():
            continue
        result.append(record)
    return result


def search_opportunity_records(*, keyword: str = "", owner_name: str = "", customer_record_id: str = "", stage: str = "") -> list[dict[str, Any]]:
    client = FeishuCrmClient()
    records = [_normalize_opportunity_record(client.app_token, item) for item in client.list_records("opportunity")]
    keyword = keyword.strip().lower()
    owner_name = owner_name.strip().lower()
    customer_record_id = customer_record_id.strip()
    stage = stage.strip().lower()
    result = []
    for record in records:
        haystack = " ".join([record.get("name", ""), record.get("customer_name", "")]).lower()
        if keyword and keyword not in haystack:
            continue
        if owner_name and owner_name not in (record.get("owner_name") or "").lower():
            continue
        if customer_record_id and customer_record_id != (record.get("customer_record_id") or ""):
            continue
        if stage and stage != (record.get("stage") or "").lower():
            continue
        result.append(record)
    return result


def _find_record_by_id(table_name: str, record_id: str) -> dict[str, Any] | None:
    if not record_id:
        return None
    client = FeishuCrmClient()
    if table_name == "customer":
        records = [_normalize_customer_record(client.app_token, item) for item in client.list_records("customer")]
    else:
        records = [_normalize_opportunity_record(client.app_token, item) for item in client.list_records("opportunity")]
    for record in records:
        if record.get("record_id") == record_id:
            return record
    return None


def bind_customer_demand_session_crm(*, session: CustomerDemandSession, provider: str, crm_customer_record_id: str = "", crm_opportunity_record_id: str = "") -> CustomerDemandSession:
    customer_record = _find_record_by_id("customer", crm_customer_record_id) if crm_customer_record_id else None
    opportunity_record = _find_record_by_id("opportunity", crm_opportunity_record_id) if crm_opportunity_record_id else None
    session.crm_provider = provider or CRM_PROVIDER
    session.crm_base_id = settings.FEISHU_BITABLE_APP_TOKEN or ""
    session.crm_customer_record_id = crm_customer_record_id or ""
    session.crm_customer_snapshot = customer_record or {}
    session.crm_opportunity_record_id = crm_opportunity_record_id or ""
    session.crm_opportunity_snapshot = opportunity_record or {}
    session.crm_bound_at = timezone.now()
    session.save(update_fields=[
        "crm_provider",
        "crm_base_id",
        "crm_customer_record_id",
        "crm_customer_snapshot",
        "crm_opportunity_record_id",
        "crm_opportunity_snapshot",
        "crm_bound_at",
        "updated_at",
    ])
    return session


def bind_solution_conversation_crm(*, conversation: Conversation, provider: str, crm_customer_record_id: str = "", crm_opportunity_record_id: str = "") -> Conversation:
    customer_record = _find_record_by_id("customer", crm_customer_record_id) if crm_customer_record_id else None
    opportunity_record = _find_record_by_id("opportunity", crm_opportunity_record_id) if crm_opportunity_record_id else None
    conversation.crm_provider = provider or CRM_PROVIDER
    conversation.crm_base_id = settings.FEISHU_BITABLE_APP_TOKEN or ""
    conversation.crm_customer_record_id = crm_customer_record_id or ""
    conversation.crm_customer_snapshot = customer_record or {}
    conversation.crm_opportunity_record_id = crm_opportunity_record_id or ""
    conversation.crm_opportunity_snapshot = opportunity_record or {}
    conversation.crm_bound_at = timezone.now()
    conversation.save(update_fields=[
        "crm_provider",
        "crm_base_id",
        "crm_customer_record_id",
        "crm_customer_snapshot",
        "crm_opportunity_record_id",
        "crm_opportunity_snapshot",
        "crm_bound_at",
        "updated_at",
    ])
    return conversation


def bind_presales_task_crm(*, task: PresalesTask, provider: str, crm_customer_record_id: str = "", crm_opportunity_record_id: str = "") -> PresalesTask:
    customer_record = _find_record_by_id("customer", crm_customer_record_id) if crm_customer_record_id else None
    opportunity_record = _find_record_by_id("opportunity", crm_opportunity_record_id) if crm_opportunity_record_id else None
    task.crm_provider = provider or CRM_PROVIDER
    task.crm_base_id = settings.FEISHU_BITABLE_APP_TOKEN or ""
    task.crm_customer_record_id = crm_customer_record_id or ""
    task.crm_customer_snapshot = customer_record or {}
    task.crm_opportunity_record_id = crm_opportunity_record_id or ""
    task.crm_opportunity_snapshot = opportunity_record or {}
    task.crm_bound_at = timezone.now()
    task.save(update_fields=[
        "crm_provider",
        "crm_base_id",
        "crm_customer_record_id",
        "crm_customer_snapshot",
        "crm_opportunity_record_id",
        "crm_opportunity_snapshot",
        "crm_bound_at",
        "updated_at",
    ])
    return task


def _build_writeback_record(*, object_type: str, object_id: str, target_table: str, action: str, created_by, request_payload: dict) -> CrmWritebackRecord:
    return CrmWritebackRecord.objects.create(
        provider=CRM_PROVIDER,
        object_type=object_type,
        object_id=str(object_id),
        target_table=target_table,
        action=action,
        status="pending",
        request_payload=request_payload,
        created_by=created_by,
    )


def _mark_writeback_success(record: CrmWritebackRecord, *, response_payload: dict[str, Any], target_record_id: str = "") -> CrmWritebackRecord:
    record.status = "success"
    record.response_payload = response_payload
    record.target_record_id = target_record_id
    record.error_message = ""
    record.save(update_fields=["status", "response_payload", "target_record_id", "error_message", "updated_at"])
    return record


def _mark_writeback_failed(record: CrmWritebackRecord, *, error_message: str, response_payload: dict[str, Any] | None = None) -> CrmWritebackRecord:
    record.status = "failed"
    record.error_message = error_message
    record.response_payload = response_payload or {}
    record.save(update_fields=["status", "error_message", "response_payload", "updated_at"])
    return record


def _join_sections(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _build_followup_fields(*, customer_record_id: str, customer_name: str, opportunity_record_id: str, opportunity_name: str, followup_type: str, summary: str, core_requirements: str = "", pending_questions: str = "", result_link: str = "", creator_name: str = "") -> dict[str, Any]:
    fmap = DEFAULT_FIELD_MAP["followup"]
    payload: dict[str, Any] = {}
    if customer_record_id:
        payload[fmap["customer_record_id"]] = [customer_record_id]
    payload[fmap["summary"]] = _join_sections(
        [
            f"跟进类型：{followup_type}",
            f"客户：{customer_name}" if customer_name else "",
            f"商机：{opportunity_name}" if opportunity_name else "",
            summary,
            f"核心内容：\n{core_requirements}" if core_requirements else "",
            f"待确认事项：\n{pending_questions}" if pending_questions else "",
            f"记录人：{creator_name}" if creator_name else "",
            f"记录时间：{timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )[:5000]
    if fmap.get("followup_form"):
        payload[fmap["followup_form"]] = "电话沟通"
    if result_link:
        payload[fmap["result_link"]] = result_link
    return payload


def _build_attachment_fields(*, customer_record_id: str, customer_name: str, opportunity_record_id: str, opportunity_name: str, file_name: str, source_type: str, file_link: str, creator_name: str = "") -> dict[str, Any]:
    fmap = DEFAULT_FIELD_MAP["attachment"]
    payload: dict[str, Any] = {}
    if customer_record_id:
        payload[fmap["customer_record_id"]] = [customer_record_id]
    payload[fmap["summary"]] = _join_sections(
        [
            "资料归档",
            f"客户：{customer_name}" if customer_name else "",
            f"商机：{opportunity_name}" if opportunity_name else "",
            f"资料名称：{file_name}",
            f"来源类型：{source_type}",
            f"上传人：{creator_name}" if creator_name else "",
            f"上传时间：{timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )[:5000]
    if fmap.get("followup_form"):
        payload[fmap["followup_form"]] = "电话沟通"
    if file_link:
        payload[fmap["result_link"]] = file_link
    return payload


def writeback_customer_demand_report(*, report: CustomerDemandReport, operator_user) -> CrmWritebackRecord:
    session = report.session
    request_payload = {
        "report_id": str(report.id),
        "session_id": str(session.id),
        "crm_customer_record_id": session.crm_customer_record_id,
        "crm_opportunity_record_id": session.crm_opportunity_record_id,
        "write_target": "followup",
    }
    record = _build_writeback_record(
        object_type="customer_demand_report",
        object_id=str(report.id),
        target_table="followup",
        action="create_record",
        created_by=operator_user,
        request_payload=request_payload,
    )
    try:
        client = FeishuCrmClient()
        payload = report.report_payload or {}
        created = client.create_record(
            "followup",
            _build_followup_fields(
                customer_record_id=session.crm_customer_record_id,
                customer_name=(session.crm_customer_snapshot or {}).get("name") or session.customer_name,
                opportunity_record_id=session.crm_opportunity_record_id,
                opportunity_name=(session.crm_opportunity_snapshot or {}).get("name") or session.topic,
                followup_type="需求分析",
                summary=(payload.get("executive_summary") or report.report_title or "需求分析报告已生成")[:500],
                core_requirements="\n".join((payload.get("explicit_requirements") or [])[:5]),
                pending_questions="\n".join((payload.get("pending_questions") or [])[:5]),
                result_link=f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/customer-demand/{session.id}/report",
                creator_name=operator_user.display_name or operator_user.username,
            ),
        )
        session.crm_last_writeback_at = timezone.now()
        session.crm_last_writeback_status = "success"
        session.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_success(record, response_payload=created, target_record_id=str((created.get("record") or {}).get("record_id") or ""))
    except (CrmIntegrationError, FeishuApiError) as exc:
        session.crm_last_writeback_at = timezone.now()
        session.crm_last_writeback_status = "failed"
        session.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_failed(record, error_message=str(exc), response_payload=getattr(exc, "response_payload", {}))


def writeback_solution_conversation(*, conversation: Conversation, operator_user) -> CrmWritebackRecord:
    assistant_message = conversation.messages.filter(role="assistant", status="completed").order_by("-created_at").first()
    if not assistant_message:
        raise CrmIntegrationError("当前解决方案会话还没有可写回 CRM 的已完成结果。")
    request_payload = {
        "conversation_id": str(conversation.id),
        "message_id": str(assistant_message.id),
        "crm_customer_record_id": conversation.crm_customer_record_id,
        "crm_opportunity_record_id": conversation.crm_opportunity_record_id,
        "write_target": "followup",
    }
    record = _build_writeback_record(
        object_type="solution_result",
        object_id=str(assistant_message.id),
        target_table="followup",
        action="create_record",
        created_by=operator_user,
        request_payload=request_payload,
    )
    try:
        client = FeishuCrmClient()
        summary = assistant_message.summary_text or assistant_message.query_text or conversation.title or "解决方案结果已生成"
        created = client.create_record(
            "followup",
            _build_followup_fields(
                customer_record_id=conversation.crm_customer_record_id,
                customer_name=(conversation.crm_customer_snapshot or {}).get("name") or "",
                opportunity_record_id=conversation.crm_opportunity_record_id,
                opportunity_name=(conversation.crm_opportunity_snapshot or {}).get("name") or conversation.title,
                followup_type="解决方案",
                summary=summary[:500],
                core_requirements=(assistant_message.content_markdown or "")[:1000],
                pending_questions="",
                result_link=f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/?conversation={conversation.id}",
                creator_name=operator_user.display_name or operator_user.username,
            ),
        )
        conversation.crm_last_writeback_at = timezone.now()
        conversation.crm_last_writeback_status = "success"
        conversation.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_success(record, response_payload=created, target_record_id=str((created.get("record") or {}).get("record_id") or ""))
    except (CrmIntegrationError, FeishuApiError) as exc:
        conversation.crm_last_writeback_at = timezone.now()
        conversation.crm_last_writeback_status = "failed"
        conversation.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_failed(record, error_message=str(exc), response_payload=getattr(exc, "response_payload", {}))


def writeback_presales_task(*, task: PresalesTask, operator_user) -> CrmWritebackRecord:
    request_payload = {
        "task_id": str(task.id),
        "crm_customer_record_id": task.crm_customer_record_id,
        "crm_opportunity_record_id": task.crm_opportunity_record_id,
        "write_target": "followup",
    }
    record = _build_writeback_record(
        object_type="presales_task",
        object_id=str(task.id),
        target_table="followup",
        action="create_record",
        created_by=operator_user,
        request_payload=request_payload,
    )
    try:
        client = FeishuCrmClient()
        summary = f"{task.task_title}（{task.get_status_display()}）"
        created = client.create_record(
            "followup",
            _build_followup_fields(
                customer_record_id=task.crm_customer_record_id,
                customer_name=(task.crm_customer_snapshot or {}).get("name") or task.customer_name,
                opportunity_record_id=task.crm_opportunity_record_id,
                opportunity_name=(task.crm_opportunity_snapshot or {}).get("name") or "",
                followup_type="售前任务",
                summary=summary,
                core_requirements=task.task_description[:1000],
                pending_questions="",
                result_link=f"{settings.PLATFORM_WEB_BASE_URL.rstrip('/')}/presales?task={task.id}",
                creator_name=operator_user.display_name or operator_user.username,
            ),
        )
        task.crm_last_writeback_at = timezone.now()
        task.crm_last_writeback_status = "success"
        task.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_success(record, response_payload=created, target_record_id=str((created.get("record") or {}).get("record_id") or ""))
    except (CrmIntegrationError, FeishuApiError) as exc:
        task.crm_last_writeback_at = timezone.now()
        task.crm_last_writeback_status = "failed"
        task.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_failed(record, error_message=str(exc), response_payload=getattr(exc, "response_payload", {}))


def writeback_archive_record(*, archive: PresalesArchiveRecord, operator_user) -> CrmWritebackRecord:
    request_payload = {
        "archive_id": str(archive.id),
        "crm_customer_record_id": archive.crm_customer_record_id,
        "crm_opportunity_record_id": archive.crm_opportunity_record_id,
        "write_target": "attachment",
    }
    record = _build_writeback_record(
        object_type="archive_record",
        object_id=str(archive.id),
        target_table="attachment",
        action="create_record",
        created_by=operator_user,
        request_payload=request_payload,
    )
    try:
        client = FeishuCrmClient()
        created = client.create_record(
            "attachment",
            _build_attachment_fields(
                customer_record_id=archive.crm_customer_record_id,
                customer_name=(archive.crm_customer_snapshot or {}).get("name") or archive.customer_name,
                opportunity_record_id=archive.crm_opportunity_record_id,
                opportunity_name=(archive.crm_opportunity_snapshot or {}).get("name") or "",
                file_name=archive.file_name or archive.source_title,
                source_type=archive.source_type,
                file_link=archive.storage_path,
                creator_name=operator_user.display_name or operator_user.username,
            ),
        )
        archive.crm_last_writeback_at = timezone.now()
        archive.crm_last_writeback_status = "success"
        archive.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_success(record, response_payload=created, target_record_id=str((created.get("record") or {}).get("record_id") or ""))
    except (CrmIntegrationError, FeishuApiError) as exc:
        archive.crm_last_writeback_at = timezone.now()
        archive.crm_last_writeback_status = "failed"
        archive.save(update_fields=["crm_last_writeback_at", "crm_last_writeback_status", "updated_at"])
        return _mark_writeback_failed(record, error_message=str(exc), response_payload=getattr(exc, "response_payload", {}))
