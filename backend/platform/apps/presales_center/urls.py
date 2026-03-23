from django.urls import path

from .views import (
    FeishuDeliveryDetailView,
    FeishuDeliveryListView,
    FeishuSyncJobListCreateView,
    PresalesArchiveListCreateView,
    PresalesTaskCompleteView,
    PresalesTaskCreateFromDemandReportView,
    PresalesTaskCreateFromSolutionView,
    PresalesTaskDetailView,
    PresalesTaskListCreateView,
    PresalesTaskSendFeishuView,
)

urlpatterns = [
    path("presales/tasks/from-demand-report", PresalesTaskCreateFromDemandReportView.as_view(), name="presales-task-from-demand-report"),
    path("presales/tasks/from-solution", PresalesTaskCreateFromSolutionView.as_view(), name="presales-task-from-solution"),
    path("presales/tasks", PresalesTaskListCreateView.as_view(), name="presales-task-list"),
    path("presales/tasks/<uuid:task_id>", PresalesTaskDetailView.as_view(), name="presales-task-detail"),
    path("presales/tasks/<uuid:task_id>/complete", PresalesTaskCompleteView.as_view(), name="presales-task-complete"),
    path("presales/tasks/<uuid:task_id>/send-feishu", PresalesTaskSendFeishuView.as_view(), name="presales-task-send-feishu"),
    path("presales/archive", PresalesArchiveListCreateView.as_view(), name="presales-archive-list"),
    path("presales/feishu/deliveries", FeishuDeliveryListView.as_view(), name="presales-feishu-delivery-list"),
    path("presales/feishu/deliveries/<uuid:delivery_id>", FeishuDeliveryDetailView.as_view(), name="presales-feishu-delivery-detail"),
    path("presales/feishu/sync-jobs", FeishuSyncJobListCreateView.as_view(), name="presales-feishu-sync-jobs"),
]
