from __future__ import annotations

from rest_framework.permissions import BasePermission


class CanUseCustomerDemand(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanExportCustomerDemand(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_permission_code("customer_demand.export")

