from django.urls import path

from .views import (
    CustomerDemandAnalyzeView,
    CustomerDemandAudioSegmentUploadView,
    CustomerDemandExportView,
    CustomerDemandRecordingDetailView,
    CustomerDemandRecordingDownloadView,
    CustomerDemandRecordingListCreateView,
    CustomerDemandReportView,
    CustomerDemandSessionDetailView,
    CustomerDemandSessionListCreateView,
    CustomerDemandStageSummariesView,
    CustomerDemandStageSummaryTriggerView,
    CustomerDemandStartView,
    CustomerDemandStopView,
    CustomerDemandPauseView,
    CustomerDemandSegmentsView,
    CustomerDemandSegmentReviewView,
    CustomerDemandTaskDetailView,
)


urlpatterns = [
    path("customer-demand/sessions", CustomerDemandSessionListCreateView.as_view(), name="customer-demand-session-list"),
    path("customer-demand/sessions/<uuid:session_id>", CustomerDemandSessionDetailView.as_view(), name="customer-demand-session-detail"),
    path("customer-demand/sessions/<uuid:session_id>/start", CustomerDemandStartView.as_view(), name="customer-demand-session-start"),
    path("customer-demand/sessions/<uuid:session_id>/pause", CustomerDemandPauseView.as_view(), name="customer-demand-session-pause"),
    path("customer-demand/sessions/<uuid:session_id>/stop", CustomerDemandStopView.as_view(), name="customer-demand-session-stop"),
    path("customer-demand/sessions/<uuid:session_id>/segments", CustomerDemandSegmentsView.as_view(), name="customer-demand-segments"),
    path("customer-demand/sessions/<uuid:session_id>/segments/<uuid:segment_id>/review", CustomerDemandSegmentReviewView.as_view(), name="customer-demand-segment-review"),
    path("customer-demand/sessions/<uuid:session_id>/segments/audio", CustomerDemandAudioSegmentUploadView.as_view(), name="customer-demand-segments-audio"),
    path("customer-demand/sessions/<uuid:session_id>/recordings", CustomerDemandRecordingListCreateView.as_view(), name="customer-demand-recordings"),
    path("customer-demand/sessions/<uuid:session_id>/recordings/<uuid:recording_id>", CustomerDemandRecordingDetailView.as_view(), name="customer-demand-recording-detail"),
    path("customer-demand/sessions/<uuid:session_id>/recordings/<uuid:recording_id>/download", CustomerDemandRecordingDownloadView.as_view(), name="customer-demand-recording-download"),
    path("customer-demand/sessions/<uuid:session_id>/stage-summaries", CustomerDemandStageSummariesView.as_view(), name="customer-demand-stage-summaries"),
    path("customer-demand/sessions/<uuid:session_id>/stage-summary", CustomerDemandStageSummaryTriggerView.as_view(), name="customer-demand-stage-summary-trigger"),
    path("customer-demand/sessions/<uuid:session_id>/analyze", CustomerDemandAnalyzeView.as_view(), name="customer-demand-analyze"),
    path("customer-demand/sessions/<uuid:session_id>/report", CustomerDemandReportView.as_view(), name="customer-demand-report"),
    path("customer-demand/sessions/<uuid:session_id>/export", CustomerDemandExportView.as_view(), name="customer-demand-export"),
    path("customer-demand/tasks/<uuid:task_id>", CustomerDemandTaskDetailView.as_view(), name="customer-demand-task-detail"),
]
