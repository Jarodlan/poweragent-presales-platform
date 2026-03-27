from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.accounts.services import resolve_visible_conversations
from apps.customer_demand.models import CustomerDemandReport
from apps.customer_demand.services import resolve_visible_customer_demand_sessions
from apps.presales_center.services import resolve_visible_presales_archives, resolve_visible_presales_tasks
from apps.presales_center.models import PresalesArchiveRecord, PresalesTask
from apps.conversations.models import Conversation

from .models import CrmWritebackRecord
from .serializers import CrmBindSerializer, CrmWritebackRequestSerializer, CrmWritebackRecordSerializer
from .services import (
    CrmIntegrationError,
    bind_customer_demand_session_crm,
    bind_presales_task_crm,
    bind_solution_conversation_crm,
    search_customer_records,
    search_opportunity_records,
    writeback_archive_record,
    writeback_customer_demand_report,
    writeback_presales_task,
    writeback_solution_conversation,
)


def _has_any_permission(user, codes: list[str]) -> bool:
    return bool(user.is_superuser or any(user.has_permission_code(code) for code in codes))


def _ensure_crm_access(user):
    if not _has_any_permission(user, ["crm.access", "crm.bind", "crm.writeback", "crm.manage"]):
        return Response({"code": 40331, "message": "无权访问 CRM 联通能力", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_crm_bind(user):
    if not _has_any_permission(user, ["crm.bind", "crm.manage"]):
        return Response({"code": 40332, "message": "无权绑定 CRM 记录", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_crm_writeback(user):
    if not _has_any_permission(user, ["crm.writeback", "crm.manage"]):
        return Response({"code": 40333, "message": "无权写回 CRM 记录", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


class CrmCustomerSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _ensure_crm_access(request.user)
        if denied:
            return denied
        keyword = (request.query_params.get("keyword") or "").strip()
        owner_name = (request.query_params.get("owner_name") or "").strip()
        try:
            items = search_customer_records(keyword=keyword, owner_name=owner_name)
        except CrmIntegrationError as exc:
            return Response({"code": 40061, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}})


class CrmOpportunitySearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _ensure_crm_access(request.user)
        if denied:
            return denied
        keyword = (request.query_params.get("keyword") or "").strip()
        owner_name = (request.query_params.get("owner_name") or "").strip()
        customer_record_id = (request.query_params.get("customer_record_id") or "").strip()
        stage = (request.query_params.get("stage") or "").strip()
        try:
            items = search_opportunity_records(
                keyword=keyword,
                owner_name=owner_name,
                customer_record_id=customer_record_id,
                stage=stage,
            )
        except CrmIntegrationError as exc:
            return Response({"code": 40062, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": 0, "message": "ok", "data": {"items": items, "total": len(items)}})


class CustomerDemandSessionCrmBindView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        denied = _ensure_crm_bind(request.user)
        if denied:
            return denied
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        serializer = CrmBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = bind_customer_demand_session_crm(session=session, **serializer.validated_data)
        except CrmIntegrationError as exc:
            return Response({"code": 40063, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": 0, "message": "ok", "data": {"session_id": str(session.id), "crm_customer_record_id": session.crm_customer_record_id, "crm_opportunity_record_id": session.crm_opportunity_record_id, "crm_customer_snapshot": session.crm_customer_snapshot, "crm_opportunity_snapshot": session.crm_opportunity_snapshot}})


class CustomerDemandReportCrmWritebackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        denied = _ensure_crm_writeback(request.user)
        if denied:
            return denied
        report = get_object_or_404(CustomerDemandReport.objects.select_related("session"), id=report_id)
        if not resolve_visible_customer_demand_sessions(request.user).filter(id=report.session_id).exists():
            return Response({"code": 40431, "message": "未找到需求分析报告", "data": None}, status=status.HTTP_404_NOT_FOUND)
        serializer = CrmWritebackRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("confirmed"):
            return Response({"code": 40064, "message": "请先确认再写回 CRM。", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        record = writeback_customer_demand_report(report=report, operator_user=request.user)
        http_status = status.HTTP_200_OK if record.status == "success" else status.HTTP_502_BAD_GATEWAY
        return Response({"code": 0 if record.status == "success" else 50264, "message": "ok" if record.status == "success" else record.error_message, "data": {"record": CrmWritebackRecordSerializer(record).data}}, status=http_status)


class ConversationCrmBindView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        denied = _ensure_crm_bind(request.user)
        if denied:
            return denied
        conversation = get_object_or_404(resolve_visible_conversations(request.user), id=conversation_id)
        serializer = CrmBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conversation = bind_solution_conversation_crm(conversation=conversation, **serializer.validated_data)
        except CrmIntegrationError as exc:
            return Response({"code": 40065, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": 0, "message": "ok", "data": {"conversation_id": str(conversation.id), "crm_customer_record_id": conversation.crm_customer_record_id, "crm_opportunity_record_id": conversation.crm_opportunity_record_id, "crm_customer_snapshot": conversation.crm_customer_snapshot, "crm_opportunity_snapshot": conversation.crm_opportunity_snapshot}})


class ConversationCrmWritebackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        denied = _ensure_crm_writeback(request.user)
        if denied:
            return denied
        conversation = get_object_or_404(resolve_visible_conversations(request.user), id=conversation_id)
        serializer = CrmWritebackRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("confirmed"):
            return Response({"code": 40066, "message": "请先确认再写回 CRM。", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        try:
            record = writeback_solution_conversation(conversation=conversation, operator_user=request.user)
        except CrmIntegrationError as exc:
            return Response({"code": 40067, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        http_status = status.HTTP_200_OK if record.status == "success" else status.HTTP_502_BAD_GATEWAY
        return Response({"code": 0 if record.status == "success" else 50267, "message": "ok" if record.status == "success" else record.error_message, "data": {"record": CrmWritebackRecordSerializer(record).data}}, status=http_status)


class PresalesTaskCrmBindView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = _ensure_crm_bind(request.user)
        if denied:
            return denied
        task = get_object_or_404(resolve_visible_presales_tasks(request.user).distinct(), id=task_id)
        serializer = CrmBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            task = bind_presales_task_crm(task=task, **serializer.validated_data)
        except CrmIntegrationError as exc:
            return Response({"code": 40068, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": 0, "message": "ok", "data": {"task_id": str(task.id), "crm_customer_record_id": task.crm_customer_record_id, "crm_opportunity_record_id": task.crm_opportunity_record_id, "crm_customer_snapshot": task.crm_customer_snapshot, "crm_opportunity_snapshot": task.crm_opportunity_snapshot}})


class PresalesTaskCrmWritebackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = _ensure_crm_writeback(request.user)
        if denied:
            return denied
        task = get_object_or_404(resolve_visible_presales_tasks(request.user).distinct(), id=task_id)
        serializer = CrmWritebackRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("confirmed"):
            return Response({"code": 40069, "message": "请先确认再写回 CRM。", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        record = writeback_presales_task(task=task, operator_user=request.user)
        http_status = status.HTTP_200_OK if record.status == "success" else status.HTTP_502_BAD_GATEWAY
        return Response({"code": 0 if record.status == "success" else 50269, "message": "ok" if record.status == "success" else record.error_message, "data": {"record": CrmWritebackRecordSerializer(record).data}}, status=http_status)


class PresalesArchiveCrmWritebackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, archive_id):
        denied = _ensure_crm_writeback(request.user)
        if denied:
            return denied
        archive = get_object_or_404(resolve_visible_presales_archives(request.user), id=archive_id)
        serializer = CrmWritebackRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("confirmed"):
            return Response({"code": 40070, "message": "请先确认再写回 CRM。", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        record = writeback_archive_record(archive=archive, operator_user=request.user)
        http_status = status.HTTP_200_OK if record.status == "success" else status.HTTP_502_BAD_GATEWAY
        return Response({"code": 0 if record.status == "success" else 50270, "message": "ok" if record.status == "success" else record.error_message, "data": {"record": CrmWritebackRecordSerializer(record).data}}, status=http_status)


class CrmWritebackRecordListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _ensure_crm_access(request.user)
        if denied:
            return denied
        object_type = (request.query_params.get("object_type") or "").strip()
        object_id = (request.query_params.get("object_id") or "").strip()
        qs = CrmWritebackRecord.objects.select_related("created_by").all()
        if object_type:
            qs = qs.filter(object_type=object_type)
        if object_id:
            qs = qs.filter(object_id=object_id)
        items = qs[:100]
        return Response({"code": 0, "message": "ok", "data": {"items": CrmWritebackRecordSerializer(items, many=True).data, "total": qs.count()}})
