from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            'id',
            'action',
            'resource_type',
            'resource_id',
            'detail_json',
            'created_at',
            'actor_name',
            'actor_username',
        )

    def get_actor_name(self, obj):
        if not obj.user:
            return '系统'
        return obj.user.display_name or obj.user.username

    def get_actor_username(self, obj):
        return obj.user.username if obj.user else 'system'
