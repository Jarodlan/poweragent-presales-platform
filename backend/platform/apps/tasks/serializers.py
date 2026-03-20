from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Task
        fields = [
            "task_id",
            "status",
            "current_step",
            "run_id",
            "error_code",
            "error_message",
            "result_payload",
            "created_at",
            "updated_at",
        ]
