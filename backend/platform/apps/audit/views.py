from __future__ import annotations

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanViewAudit

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [CanViewAudit]

    def get(self, request):
        qs = AuditLog.objects.select_related('user').all().order_by('-created_at')
        action = request.query_params.get('action')
        resource_type = request.query_params.get('resource_type')
        actor_id = request.query_params.get('actor_id')
        keyword = request.query_params.get('keyword')

        if action:
            qs = qs.filter(action=action)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if actor_id:
            qs = qs.filter(user_id=actor_id)
        if keyword:
            qs = qs.filter(
                Q(action__icontains=keyword)
                | Q(resource_type__icontains=keyword)
                | Q(resource_id__icontains=keyword)
                | Q(detail_json__icontains=keyword)
                | Q(user__username__icontains=keyword)
                | Q(user__display_name__icontains=keyword)
            )

        items = AuditLogSerializer(qs[:300], many=True).data
        return Response({'code': 0, 'message': 'ok', 'data': {'items': items}})
