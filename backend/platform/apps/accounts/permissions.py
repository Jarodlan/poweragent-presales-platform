from __future__ import annotations

from rest_framework.permissions import BasePermission


class HasPermissionCode(BasePermission):
    permission_code: str | None = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if not self.permission_code:
            return True
        return request.user.has_permission_code(self.permission_code)


class CanManageUsers(HasPermissionCode):
    permission_code = "user.manage"


class CanManageRoles(HasPermissionCode):
    permission_code = "role.manage"


class CanManageDepartments(HasPermissionCode):
    permission_code = "department.manage"


class CanViewAudit(HasPermissionCode):
    permission_code = "audit.view"
