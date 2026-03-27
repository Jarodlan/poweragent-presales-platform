from django.urls import path

from .views import (
    ConversationCrmBindView,
    ConversationCrmWritebackView,
    CrmCustomerSearchView,
    CrmOpportunitySearchView,
    CrmWritebackRecordListView,
    CustomerDemandReportCrmWritebackView,
    CustomerDemandSessionCrmBindView,
    PresalesArchiveCrmWritebackView,
    PresalesTaskCrmBindView,
    PresalesTaskCrmWritebackView,
)

urlpatterns = [
    path("crm/customers", CrmCustomerSearchView.as_view(), name="crm-customer-search"),
    path("crm/opportunities", CrmOpportunitySearchView.as_view(), name="crm-opportunity-search"),
    path("crm/writebacks", CrmWritebackRecordListView.as_view(), name="crm-writeback-record-list"),
    path("customer-demand/sessions/<uuid:session_id>/crm-bind", CustomerDemandSessionCrmBindView.as_view(), name="customer-demand-session-crm-bind"),
    path("customer-demand/reports/<uuid:report_id>/crm-writeback", CustomerDemandReportCrmWritebackView.as_view(), name="customer-demand-report-crm-writeback"),
    path("conversations/<uuid:conversation_id>/crm-bind", ConversationCrmBindView.as_view(), name="conversation-crm-bind"),
    path("conversations/<uuid:conversation_id>/crm-writeback", ConversationCrmWritebackView.as_view(), name="conversation-crm-writeback"),
    path("presales/tasks/<uuid:task_id>/crm-bind", PresalesTaskCrmBindView.as_view(), name="presales-task-crm-bind"),
    path("presales/tasks/<uuid:task_id>/crm-writeback", PresalesTaskCrmWritebackView.as_view(), name="presales-task-crm-writeback"),
    path("presales/archive/<uuid:archive_id>/crm-writeback", PresalesArchiveCrmWritebackView.as_view(), name="presales-archive-crm-writeback"),
]
