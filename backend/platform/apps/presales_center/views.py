from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FeishuDeliveryRecord, FeishuSyncJob, PresalesArchiveRecord, PresalesTask
from .serializers import (
    FeishuDeliveryRecordSerializer,
    FeishuSendSerializer,
    FeishuSyncJobCreateSerializer,
    FeishuSyncJobSerializer,
    PresalesArchiveRecordSerializer,
    PresalesArchiveRecordWriteSerializer,
    PresalesTaskFromDemandReportSerializer,
    PresalesTaskFromSolutionSerializer,
    PresalesTaskSerializer,
    PresalesTaskWriteSerializer,
)
from .services import (
    complete_presales_task,
    create_presales_task,
    create_task_from_demand_report,
    create_task_from_solution_result,
    deliver_feishu_record,
    queue_feishu_delivery,
    resolve_visible_presales_archives,
    resolve_visible_presales_tasks,
    run_feishu_sync_job,
    update_presales_task,
)


def _has_any_permission(user, codes: list[str]) -> bool:
    return bool(user.is_superuser or any(user.has_permission_code(code) for code in codes))


def _ensure_presales_access(user):
    if not _has_any_permission(user, ["presales_center.access", "presales_task.view", "presales_task.manage"]):
        return Response({"code": 40301, "message": "无权访问售前闭环模块", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_task_manage(user):
    if not _has_any_permission(user, ["presales_task.manage"]):
        return Response({"code": 40302, "message": "无权管理售前任务", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_task_view(user):
    if not _has_any_permission(user, ["presales_task.view", "presales_task.manage"]):
        return Response({"code": 40303, "message": "无权查看售前任务", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_archive_view(user):
    if not _has_any_permission(user, ["presales_archive.view", "presales_archive.manage"]):
        return Response({"code": 40304, "message": "无权查看售前归档", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_archive_manage(user):
    if not _has_any_permission(user, ["presales_archive.manage"]):
        return Response({"code": 40305, "message": "无权管理售前归档", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_delivery_view(user):
    if not _has_any_permission(user, ["feishu_delivery.view", "feishu_delivery.manage"]):
        return Response({"code": 40306, "message": "无权查看飞书发送记录", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_delivery_manage(user):
    if not _has_any_permission(user, ["feishu_delivery.manage", "presales_task.manage"]):
        return Response({"code": 40307, "message": "无权发起飞书发送", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


def _ensure_sync_manage(user):
    if not _has_any_permission(user, ["feishu_sync.manage"]):
        return Response({"code": 40308, "message": "无权触发飞书同步任务", "data": None}, status=status.HTTP_403_FORBIDDEN)
    return None


class PresalesTaskCreateFromDemandReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        denied = _ensure_presales_access(request.user) or _ensure_task_manage(request.user)
        if denied:
            return denied
        serializer = PresalesTaskFromDemandReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_task_from_demand_report(created_by=request.user, **serializer.validated_data)
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}}, status=status.HTTP_201_CREATED)


class PresalesTaskCreateFromSolutionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        denied = _ensure_presales_access(request.user) or _ensure_task_manage(request.user)
        if denied:
            return denied
        serializer = PresalesTaskFromSolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_task_from_solution_result(created_by=request.user, **serializer.validated_data)
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}}, status=status.HTTP_201_CREATED)


class PresalesTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = resolve_visible_presales_tasks(request.user)
        keyword = (request.query_params.get("keyword") or "").strip()
        status_value = (request.query_params.get("status") or "").strip()
        priority = (request.query_params.get("priority") or "").strip()
        source_type = (request.query_params.get("source_type") or "").strip()
        assignee_user_id = (request.query_params.get("assignee_user_id") or "").strip()
        customer_name = (request.query_params.get("customer_name") or "").strip()
        feishu_delivery_status = (request.query_params.get("feishu_delivery_status") or "").strip()
        due_from = (request.query_params.get("due_from") or "").strip()
        due_to = (request.query_params.get("due_to") or "").strip()
        followup_from = (request.query_params.get("followup_from") or "").strip()
        followup_to = (request.query_params.get("followup_to") or "").strip()

        if keyword:
            qs = qs.filter(Q(task_title__icontains=keyword) | Q(task_description__icontains=keyword) | Q(customer_name__icontains=keyword))
        if status_value:
            qs = qs.filter(status=status_value)
        if priority:
            qs = qs.filter(priority=priority)
        if source_type:
            qs = qs.filter(source_type=source_type)
        if assignee_user_id:
            qs = qs.filter(assignee_user_id=assignee_user_id)
        if customer_name:
            qs = qs.filter(customer_name__icontains=customer_name)
        if feishu_delivery_status:
            qs = qs.filter(feishu_delivery_status=feishu_delivery_status)
        if due_from:
            qs = qs.filter(due_at__date__gte=due_from)
        if due_to:
            qs = qs.filter(due_at__date__lte=due_to)
        if followup_from:
            qs = qs.filter(next_follow_up_at__date__gte=followup_from)
        if followup_to:
            qs = qs.filter(next_follow_up_at__date__lte=followup_to)
        return qs.order_by("-updated_at")

    def get(self, request):
        denied = _ensure_presales_access(request.user) or _ensure_task_view(request.user)
        if denied:
            return denied
        qs = self.get_queryset(request)
        items = qs[:200]
        return Response({"code": 0, "message": "ok", "data": {"items": PresalesTaskSerializer(items, many=True).data, "total": qs.count()}})

    def post(self, request):
        denied = _ensure_presales_access(request.user) or _ensure_task_manage(request.user)
        if denied:
            return denied
        serializer = PresalesTaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = create_presales_task(
            created_by=request.user,
            owner_user=data.get("owner_user") or request.user,
            owner_department=data.get("owner_department") or getattr(request.user, "department", None),
            assignee_user=data.get("assignee_user"),
            task_title=data["task_title"],
            task_type=data.get("task_type", "manual"),
            task_description=data.get("task_description", ""),
            source_type=data.get("source_type", "manual"),
            source_id=data.get("source_id", ""),
            source_version=data.get("source_version"),
            customer_name=data.get("customer_name", ""),
            customer_id=data.get("customer_id", ""),
            priority=data.get("priority", "medium"),
            due_at=data.get("due_at"),
            next_follow_up_at=data.get("next_follow_up_at"),
            collaborator_user_ids=data.get("collaborator_user_ids"),
            payload_json=data.get("payload_json") or {},
        )
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}}, status=status.HTTP_201_CREATED)


class PresalesTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, task_id):
        return get_object_or_404(resolve_visible_presales_tasks(request.user).distinct(), id=task_id)

    def get(self, request, task_id):
        denied = _ensure_presales_access(request.user) or _ensure_task_view(request.user)
        if denied:
            return denied
        task = self.get_object(request, task_id)
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}})

    def patch(self, request, task_id):
        denied = _ensure_presales_access(request.user) or _ensure_task_manage(request.user)
        if denied:
            return denied
        task = self.get_object(request, task_id)
        serializer = PresalesTaskWriteSerializer(instance=task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = update_presales_task(task, operator_user=request.user, validated_updates=serializer.validated_data)
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}})


class PresalesTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = _ensure_presales_access(request.user) or _ensure_task_manage(request.user)
        if denied:
            return denied
        task = get_object_or_404(resolve_visible_presales_tasks(request.user).distinct(), id=task_id)
        summary = (request.data.get("summary") or "").strip()
        task = complete_presales_task(task, operator_user=request.user, summary=summary)
        return Response({"code": 0, "message": "ok", "data": {"task": PresalesTaskSerializer(task).data}})


class PresalesTaskSendFeishuView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        denied = _ensure_presales_access(request.user) or _ensure_delivery_manage(request.user)
        if denied:
            return denied
        task = get_object_or_404(resolve_visible_presales_tasks(request.user).distinct(), id=task_id)
        serializer = FeishuSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delivery = queue_feishu_delivery(
            operator_user=request.user,
            business_type="presales_task_notification",
            business_id=str(task.id),
            target_type=serializer.validated_data["target_type"],
            target_id=serializer.validated_data["target_id"],
            target_name=serializer.validated_data.get("target_name", ""),
            message_type=serializer.validated_data["message_type"],
            request_payload=serializer.validated_data.get("message_payload") or {},
        )
        try:
            delivery = deliver_feishu_record(delivery, operator_user=request.user)
        except Exception as exc:  # noqa: BLE001
            task.latest_feishu_delivery = delivery
            task.feishu_delivery_status = delivery.delivery_status
            task.save(update_fields=["latest_feishu_delivery", "feishu_delivery_status", "updated_at"])
            return Response(
                {
                    "code": 50031,
                    "message": f"飞书发送失败：{exc}",
                    "data": {"delivery": FeishuDeliveryRecordSerializer(delivery).data},
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        task.latest_feishu_delivery = delivery
        task.feishu_delivery_status = delivery.delivery_status
        task.save(update_fields=["latest_feishu_delivery", "feishu_delivery_status", "updated_at"])
        return Response({"code": 0, "message": "ok", "data": {"delivery": FeishuDeliveryRecordSerializer(delivery).data}})


class PresalesArchiveListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = resolve_visible_presales_archives(request.user)
        archive_type = (request.query_params.get("archive_type") or "").strip()
        source_type = (request.query_params.get("source_type") or "").strip()
        customer_name = (request.query_params.get("customer_name") or "").strip()
        keyword = (request.query_params.get("keyword") or "").strip()
        if archive_type:
            qs = qs.filter(archive_type=archive_type)
        if source_type:
            qs = qs.filter(source_type=source_type)
        if customer_name:
            qs = qs.filter(customer_name__icontains=customer_name)
        if keyword:
            qs = qs.filter(Q(source_title__icontains=keyword) | Q(file_name__icontains=keyword))
        return qs.order_by("-created_at")

    def get(self, request):
        denied = _ensure_archive_view(request.user)
        if denied:
            return denied
        qs = self.get_queryset(request)
        return Response({"code": 0, "message": "ok", "data": {"items": PresalesArchiveRecordSerializer(qs[:200], many=True).data, "total": qs.count()}})

    def post(self, request):
        denied = _ensure_archive_manage(request.user)
        if denied:
            return denied
        serializer = PresalesArchiveRecordWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        archive = serializer.save(uploaded_by=request.user)
        return Response({"code": 0, "message": "ok", "data": {"archive": PresalesArchiveRecordSerializer(archive).data}}, status=status.HTTP_201_CREATED)


class FeishuDeliveryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _ensure_delivery_view(request.user)
        if denied:
            return denied
        qs = FeishuDeliveryRecord.objects.select_related("operator_user")
        business_type = (request.query_params.get("business_type") or "").strip()
        delivery_status = (request.query_params.get("delivery_status") or "").strip()
        target_type = (request.query_params.get("target_type") or "").strip()
        target_id = (request.query_params.get("target_id") or "").strip()
        if business_type:
            qs = qs.filter(business_type=business_type)
        if delivery_status:
            qs = qs.filter(delivery_status=delivery_status)
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id__icontains=target_id)
        return Response({"code": 0, "message": "ok", "data": {"items": FeishuDeliveryRecordSerializer(qs[:200], many=True).data, "total": qs.count()}})


class FeishuDeliveryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, delivery_id):
        denied = _ensure_delivery_view(request.user)
        if denied:
            return denied
        delivery = get_object_or_404(FeishuDeliveryRecord.objects.select_related("operator_user"), id=delivery_id)
        return Response({"code": 0, "message": "ok", "data": {"delivery": FeishuDeliveryRecordSerializer(delivery).data}})


class FeishuSyncJobListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _ensure_sync_manage(request.user)
        if denied:
            return denied
        qs = FeishuSyncJob.objects.select_related("operator_user").order_by("-created_at")
        return Response({"code": 0, "message": "ok", "data": {"items": FeishuSyncJobSerializer(qs[:100], many=True).data, "total": qs.count()}})

    def post(self, request):
        denied = _ensure_sync_manage(request.user)
        if denied:
            return denied
        serializer = FeishuSyncJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(operator_user=request.user, trigger_type="manual", status="pending")
        try:
            job = run_feishu_sync_job(job, operator_user=request.user)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {
                    "code": 50032,
                    "message": f"飞书同步失败：{exc}",
                    "data": {"job": FeishuSyncJobSerializer(job).data},
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"code": 0, "message": "ok", "data": {"job": FeishuSyncJobSerializer(job).data}}, status=status.HTTP_201_CREATED)
