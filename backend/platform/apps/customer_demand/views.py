from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .asr.service import transcribe_audio_chunk
from .models import CustomerDemandAnalysisTask, CustomerDemandReport, CustomerDemandSegment, CustomerDemandSession, CustomerDemandStageSummary
from .permissions import CanExportCustomerDemand
from .semantic import validate_segment_semantics
from .serializers import (
    CustomerDemandAnalysisTaskSerializer,
    CustomerDemandReportSerializer,
    CustomerDemandSegmentSerializer,
    CustomerDemandSegmentWriteSerializer,
    CustomerDemandSessionSerializer,
    CustomerDemandSessionWriteSerializer,
    CustomerDemandStageSummarySerializer,
)
from .services import enqueue_final_report, enqueue_stage_summary, resolve_visible_customer_demand_sessions


class CustomerDemandSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = resolve_visible_customer_demand_sessions(request.user)
        keyword = request.query_params.get("keyword", "").strip()
        status_value = request.query_params.get("status", "").strip()
        industry = request.query_params.get("industry", "").strip()
        region = request.query_params.get("region", "").strip()
        if keyword:
            qs = qs.filter(Q(customer_name__icontains=keyword) | Q(session_title__icontains=keyword))
        if status_value:
            qs = qs.filter(status=status_value)
        if industry:
            qs = qs.filter(industry=industry)
        if region:
            qs = qs.filter(region=region)
        return qs.order_by("-updated_at")

    def get(self, request):
        qs = self.get_queryset(request)[:50]
        return Response({"code": 0, "message": "ok", "data": {"items": CustomerDemandSessionSerializer(qs, many=True).data, "total": qs.count()}})

    def post(self, request):
        serializer = CustomerDemandSessionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(owner=request.user, department=request.user.department)
        return Response({"code": 0, "message": "ok", "data": CustomerDemandSessionSerializer(session).data}, status=status.HTTP_201_CREATED)


class CustomerDemandSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, session_id):
        return get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)

    def get(self, request, session_id):
        session = self.get_object(request, session_id)
        return Response({"code": 0, "message": "ok", "data": CustomerDemandSessionSerializer(session).data})

    def patch(self, request, session_id):
        session = self.get_object(request, session_id)
        serializer = CustomerDemandSessionWriteSerializer(instance=session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response({"code": 0, "message": "ok", "data": CustomerDemandSessionSerializer(session).data})


class CustomerDemandStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        session.status = "recording"
        session.recording_started_at = timezone.now()
        session.save(update_fields=["status", "recording_started_at", "updated_at"])
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "session_id": str(session.id),
                    "status": session.status,
                    "asr_upload_url": f"/api/v1/customer-demand/sessions/{session.id}/segments/audio",
                    "stream_url": f"/api/v1/customer-demand/sessions/{session.id}/stream",
                },
            }
        )


class CustomerDemandPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        session.status = "paused"
        session.save(update_fields=["status", "updated_at"])
        return Response({"code": 0, "message": "ok", "data": {"session_id": str(session.id), "status": session.status}})


class CustomerDemandStopView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        session.status = "closed"
        session.recording_stopped_at = timezone.now()
        session.save(update_fields=["status", "recording_stopped_at", "updated_at"])
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "session_id": str(session.id),
                    "status": session.status,
                    "recording_stopped_at": session.recording_stopped_at.isoformat(),
                },
            }
        )


class CustomerDemandSegmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_session(self, request, session_id):
        return get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)

    def get(self, request, session_id):
        session = self.get_session(request, session_id)
        items = session.segments.order_by("sequence_no", "created_at")[:200]
        return Response({"code": 0, "message": "ok", "data": {"items": CustomerDemandSegmentSerializer(items, many=True).data}})

    def post(self, request, session_id):
        session = self.get_session(request, session_id)
        serializer = CustomerDemandSegmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        segment = serializer.save(session=session)
        segment = validate_segment_semantics(session, segment)
        if segment.final_text or segment.normalized_text:
            session.normalized_segment_count = session.segments.filter(segment_status="normalized").count()
        session.raw_segment_count = session.segments.count()
        session.save(update_fields=["raw_segment_count", "normalized_segment_count", "updated_at"])
        return Response({"code": 0, "message": "ok", "data": CustomerDemandSegmentSerializer(segment).data}, status=status.HTTP_201_CREATED)


class CustomerDemandSegmentReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, segment_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        segment = get_object_or_404(CustomerDemandSegment.objects.filter(session=session), id=segment_id)
        decision = (request.data.get("decision") or "").strip()
        edited_text = (request.data.get("edited_text") or "").strip()
        note = (request.data.get("note") or "").strip()

        if decision not in {"accept", "discard"}:
            return Response(
                {"code": 40040, "message": "decision 仅支持 accept 或 discard", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if edited_text:
            segment.normalized_text = edited_text
            segment.final_text = edited_text

        if decision == "accept":
            segment.segment_status = "normalized"
            segment.review_flag = False
        else:
            segment.segment_status = "discarded"
            segment.review_flag = True

        issues = [str(item) for item in (segment.issues_json or []) if str(item).strip()]
        if note:
            issues.append(f"人工复核备注：{note}")
        segment.issues_json = list(dict.fromkeys(issues))
        segment.save(
            update_fields=[
                "normalized_text",
                "final_text",
                "segment_status",
                "review_flag",
                "issues_json",
                "updated_at",
            ]
        )
        session.normalized_segment_count = session.segments.filter(segment_status="normalized").count()
        session.raw_segment_count = session.segments.count()
        session.save(update_fields=["raw_segment_count", "normalized_segment_count", "updated_at"])
        return Response({"code": 0, "message": "ok", "data": CustomerDemandSegmentSerializer(segment).data})


class CustomerDemandAudioSegmentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        chunk_index = int(request.data.get("chunk_index", 0))
        provider = request.data.get("provider", "")
        sample_rate = int(request.data.get("audio_fs", 16000))
        language = request.data.get("language", "zh")
        mock_text = (request.data.get("mock_text") or "").strip()
        audio_file = request.FILES.get("audio_chunk")
        audio_bytes = audio_file.read() if audio_file else b""

        if mock_text:
            result_text = mock_text
            raw_text = mock_text
            confidence = None
            review_flag = False
            issues = []
            metadata = {"provider": provider or "mock", "mode": "mock_text"}
        else:
            transcript = transcribe_audio_chunk(
                audio_bytes=audio_bytes,
                provider=provider or None,
                sample_rate=sample_rate,
                language=language,
                metadata={
                    "session_id": str(session.id),
                    "chunk_index": chunk_index,
                    "content_type": getattr(audio_file, "content_type", "") if audio_file else "",
                    "file_name": getattr(audio_file, "name", "") if audio_file else "",
                    "file_size": len(audio_bytes),
                },
            )
            result_text = transcript.text
            raw_text = transcript.raw_text
            confidence = transcript.confidence
            review_flag = transcript.review_flag
            issues = transcript.issues
            metadata = transcript.metadata

        segment = CustomerDemandSegment.objects.create(
            session=session,
            sequence_no=max(chunk_index, session.segments.count() + 1),
            speaker_label=request.data.get("speaker_label", ""),
            raw_text=raw_text,
            normalized_text=result_text,
            final_text=result_text,
            asr_provider=(provider or metadata.get("provider") or ""),
            confidence_score=confidence,
            review_flag=review_flag,
            issues_json=issues,
            raw_start_ms=request.data.get("started_at_ms") or None,
            raw_end_ms=request.data.get("ended_at_ms") or None,
            segment_status="review_required" if review_flag else "normalized",
        )
        segment = validate_segment_semantics(session, segment)
        session.raw_segment_count = session.segments.count()
        session.normalized_segment_count = session.segments.filter(segment_status="normalized").count()
        session.save(update_fields=["raw_segment_count", "normalized_segment_count", "updated_at"])

        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "accepted": True,
                    "chunk_index": chunk_index,
                    "session_id": str(session.id),
                    "segment": CustomerDemandSegmentSerializer(segment).data,
                    "adapter_metadata": metadata,
                },
            }
        )


class CustomerDemandStageSummariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        items = session.stage_summaries.order_by("-summary_version", "-created_at")[:20]
        return Response({"code": 0, "message": "ok", "data": {"items": CustomerDemandStageSummarySerializer(items, many=True).data}})


class CustomerDemandStageSummaryTriggerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        trigger_type = request.data.get("trigger_type", "manual")
        task = enqueue_stage_summary(session=session, trigger_type=trigger_type, created_by=request.user)
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "task": CustomerDemandAnalysisTaskSerializer(task).data,
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CustomerDemandAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        knowledge_enabled = bool(request.data.get("knowledge_enabled", session.knowledge_enabled))
        task = enqueue_final_report(session=session, created_by=request.user, knowledge_enabled=knowledge_enabled)
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "task": CustomerDemandAnalysisTaskSerializer(task).data,
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CustomerDemandReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        report = session.reports.order_by("-report_version", "-created_at").first()
        if not report:
            return Response({"code": 0, "message": "ok", "data": None})
        return Response({"code": 0, "message": "ok", "data": CustomerDemandReportSerializer(report).data})


class CustomerDemandTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(CustomerDemandAnalysisTask.objects.select_related("session"), id=task_id)
        visible_sessions = resolve_visible_customer_demand_sessions(request.user)
        if not visible_sessions.filter(id=task.session_id).exists():
            return Response({"code": 404, "message": "not found", "data": None}, status=status.HTTP_404_NOT_FOUND)
        return Response({"code": 0, "message": "ok", "data": CustomerDemandAnalysisTaskSerializer(task).data})


class CustomerDemandExportView(APIView):
    permission_classes = [CanExportCustomerDemand]

    def post(self, request, session_id):
        session = get_object_or_404(resolve_visible_customer_demand_sessions(request.user), id=session_id)
        report = session.reports.order_by("-report_version", "-created_at").first()
        if not report:
            return Response({"code": 40050, "message": "当前会话暂无可导出报告", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        format_value = request.data.get("format", "markdown")
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "session_id": str(session.id),
                    "report_id": str(report.id),
                    "format": format_value,
                    "content": report.report_markdown,
                },
            }
        )
