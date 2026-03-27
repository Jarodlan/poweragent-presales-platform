from __future__ import annotations

from rest_framework import serializers

from .models import CrmWritebackRecord


class CrmRecordSerializer(serializers.Serializer):
    provider = serializers.CharField()
    base_id = serializers.CharField()
    table = serializers.CharField()
    record_id = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True)
    industry = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(required=False, allow_blank=True)
    level = serializers.CharField(required=False, allow_blank=True)
    owner_name = serializers.CharField(required=False, allow_blank=True)
    last_followup_at = serializers.CharField(required=False, allow_blank=True)
    customer_record_id = serializers.CharField(required=False, allow_blank=True)
    stage = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.CharField(required=False, allow_blank=True)
    next_followup_at = serializers.CharField(required=False, allow_blank=True)


class CrmBindSerializer(serializers.Serializer):
    provider = serializers.CharField(default="feishu_bitable")
    crm_customer_record_id = serializers.CharField(required=False, allow_blank=True)
    crm_opportunity_record_id = serializers.CharField(required=False, allow_blank=True)


class CrmWritebackRequestSerializer(serializers.Serializer):
    write_target = serializers.ChoiceField(choices=["followup", "attachment"], default="followup")
    mode = serializers.ChoiceField(choices=["append", "update"], default="append")
    confirmed = serializers.BooleanField(default=False)
    sync_next_followup = serializers.BooleanField(default=False)


class CrmWritebackRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrmWritebackRecord
        fields = (
            "id",
            "provider",
            "object_type",
            "object_id",
            "target_table",
            "target_record_id",
            "action",
            "status",
            "request_payload",
            "response_payload",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
        )
