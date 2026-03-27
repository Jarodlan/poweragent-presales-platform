from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Department, User
from apps.accounts.serializers import DepartmentSerializer, UserSerializer
from apps.customer_demand.models import CustomerDemandReport

from .models import FeishuDeliveryRecord, FeishuSyncJob, PresalesArchiveRecord, PresalesTask, PresalesTaskActivity


class PresalesTaskActivitySerializer(serializers.ModelSerializer):
    operator_user = UserSerializer(read_only=True)

    class Meta:
        model = PresalesTaskActivity
        fields = (
            "id",
            "activity_type",
            "operator_user",
            "from_status",
            "to_status",
            "summary",
            "details_markdown",
            "payload_json",
            "created_at",
        )


class FeishuDeliveryRecordSerializer(serializers.ModelSerializer):
    operator_user = UserSerializer(read_only=True)

    class Meta:
        model = FeishuDeliveryRecord
        fields = (
            "id",
            "business_type",
            "business_id",
            "target_type",
            "target_id",
            "target_name",
            "message_type",
            "request_payload",
            "response_payload",
            "delivery_status",
            "error_code",
            "error_message",
            "retry_count",
            "operator_user",
            "created_at",
            "updated_at",
        )


class PresalesTaskSerializer(serializers.ModelSerializer):
    owner_user = UserSerializer(read_only=True)
    owner_department = DepartmentSerializer(read_only=True)
    assignee_user = UserSerializer(read_only=True)
    latest_feishu_delivery = FeishuDeliveryRecordSerializer(read_only=True)
    activities = PresalesTaskActivitySerializer(read_only=True, many=True)

    class Meta:
        model = PresalesTask
        fields = (
            "id",
            "task_title",
            "task_type",
            "task_description",
            "source_type",
            "source_id",
            "source_version",
            "customer_name",
            "customer_id",
            "owner_user",
            "owner_department",
            "assignee_user",
            "collaborator_user_ids",
            "status",
            "priority",
            "due_at",
            "next_follow_up_at",
            "crm_provider",
            "crm_base_id",
            "crm_customer_record_id",
            "crm_customer_snapshot",
            "crm_opportunity_record_id",
            "crm_opportunity_snapshot",
            "crm_bound_at",
            "crm_last_writeback_at",
            "crm_last_writeback_status",
            "followup_status",
            "feishu_delivery_status",
            "latest_feishu_delivery",
            "payload_json",
            "is_archived",
            "archived_at",
            "created_by",
            "created_at",
            "updated_at",
            "activities",
        )
        depth = 0


class PresalesTaskWriteSerializer(serializers.ModelSerializer):
    assignee_user_id = serializers.PrimaryKeyRelatedField(source="assignee_user", queryset=User.objects.all(), allow_null=True, required=False)
    owner_user_id = serializers.PrimaryKeyRelatedField(source="owner_user", queryset=User.objects.all(), allow_null=True, required=False)
    owner_department_id = serializers.PrimaryKeyRelatedField(source="owner_department", queryset=Department.objects.all(), allow_null=True, required=False)
    collaborator_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, allow_empty=True)

    class Meta:
        model = PresalesTask
        fields = (
            "task_title",
            "task_type",
            "task_description",
            "source_type",
            "source_id",
            "source_version",
            "customer_name",
            "customer_id",
            "owner_user_id",
            "owner_department_id",
            "assignee_user_id",
            "collaborator_user_ids",
            "status",
            "priority",
            "due_at",
            "next_follow_up_at",
            "payload_json",
        )


class PresalesTaskFromDemandReportSerializer(serializers.Serializer):
    report_id = serializers.PrimaryKeyRelatedField(queryset=CustomerDemandReport.objects.select_related("session", "session__owner", "session__department"), source="report")
    task_title = serializers.CharField(max_length=255)
    task_description = serializers.CharField(required=False, allow_blank=True)
    assignee_user_id = serializers.PrimaryKeyRelatedField(source="assignee_user", queryset=User.objects.all(), required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=PresalesTask.PRIORITY_CHOICES, default="medium")
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    next_follow_up_at = serializers.DateTimeField(required=False, allow_null=True)
    collaborator_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, allow_empty=True)
    payload_json = serializers.JSONField(required=False)


class PresalesTaskFromSolutionSerializer(serializers.Serializer):
    source_id = serializers.CharField(max_length=128)
    source_title = serializers.CharField(max_length=255)
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    task_title = serializers.CharField(max_length=255)
    task_description = serializers.CharField(required=False, allow_blank=True)
    assignee_user_id = serializers.PrimaryKeyRelatedField(source="assignee_user", queryset=User.objects.all(), required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=PresalesTask.PRIORITY_CHOICES, default="medium")
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    next_follow_up_at = serializers.DateTimeField(required=False, allow_null=True)
    collaborator_user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, allow_empty=True)
    payload_json = serializers.JSONField(required=False)


class PresalesArchiveRecordSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = PresalesArchiveRecord
        fields = (
            "id",
            "archive_type",
            "source_type",
            "source_id",
            "source_version",
            "customer_name",
            "source_title",
            "file_name",
            "mime_type",
            "storage_provider",
            "storage_path",
            "storage_bucket",
            "archive_status",
            "feishu_shared",
            "crm_provider",
            "crm_base_id",
            "crm_customer_record_id",
            "crm_customer_snapshot",
            "crm_opportunity_record_id",
            "crm_opportunity_snapshot",
            "crm_bound_at",
            "crm_last_writeback_at",
            "crm_last_writeback_status",
            "metadata_json",
            "uploaded_by",
            "created_at",
            "updated_at",
        )


class PresalesArchiveRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresalesArchiveRecord
        fields = (
            "archive_type",
            "source_type",
            "source_id",
            "source_version",
            "customer_name",
            "source_title",
            "file_name",
            "mime_type",
            "storage_provider",
            "storage_path",
            "storage_bucket",
            "metadata_json",
        )


class FeishuSendSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=FeishuDeliveryRecord.TARGET_TYPE_CHOICES)
    target_id = serializers.CharField(max_length=128)
    target_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message_type = serializers.ChoiceField(choices=FeishuDeliveryRecord.MESSAGE_TYPE_CHOICES, default="interactive_card")
    message_payload = serializers.JSONField(required=False)


class FeishuSyncJobSerializer(serializers.ModelSerializer):
    operator_user = UserSerializer(read_only=True)

    class Meta:
        model = FeishuSyncJob
        fields = (
            "id",
            "job_type",
            "trigger_type",
            "status",
            "started_at",
            "finished_at",
            "synced_user_count",
            "synced_department_count",
            "disabled_user_count",
            "error_count",
            "summary_json",
            "error_message",
            "operator_user",
            "created_at",
            "updated_at",
        )


class FeishuSyncJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeishuSyncJob
        fields = ("job_type",)
