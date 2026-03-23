from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.conversations.models import Conversation
from apps.tasks.models import Task

from .authentication import ExpiringTokenAuthentication, TOKEN_VALIDITY_DAYS
from .models import Department, Permission, Role, User
from .permissions import CanManageDepartments, CanManageRoles, CanManageUsers
from .serializers import (
    DepartmentSerializer,
    DepartmentWriteSerializer,
    LoginSerializer,
    PermissionSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from .services import record_login_failure, record_login_success


SOLUTION_MODULE_PERMISSION_CODES = [
    "conversation.view",
    "conversation.manage_department",
    "conversation.manage_all",
    "task.view",
    "task.manage_department",
    "task.manage_all",
]

CUSTOMER_DEMAND_MODULE_PERMISSION_CODES = [
    "customer_demand.view",
    "customer_demand.create",
    "customer_demand.manage_all",
    "customer_demand.export",
]


def _user_has_any_permission(user: User, codes: list[str]) -> bool:
    return bool(user.is_superuser or any(code in user.get_permission_codes() for code in codes))


def _build_platform_modules_for_user(user: User) -> list[dict]:
    modules: list[dict] = []

    if _user_has_any_permission(user, SOLUTION_MODULE_PERMISSION_CODES):
        modules.append(
            {
                "module_id": "solution_workspace",
                "name": "解决方案智能体",
                "description": "基于场景、参数、知识库与模板生成行业解决方案。",
                "icon": "Cpu",
                "route_type": "internal",
                "route_target": "/",
                "open_mode": "same_tab",
            }
        )

    if _user_has_any_permission(user, CUSTOMER_DEMAND_MODULE_PERMISSION_CODES):
        modules.append(
            {
                "module_id": "customer_demand_workspace",
                "name": "客户需求分析智能体",
                "description": "会中记录客户沟通，生成阶段整理、需求分析报告与建议追问。",
                "icon": "ChatDotRound",
                "route_type": "internal",
                "route_target": "/customer-demand",
                "open_mode": "same_tab",
            }
        )

    if _user_has_any_permission(user, ["knowledge.manage"]):
        modules.append(
            {
                "module_id": "knowledge_base_admin",
                "name": "知识库管理",
                "description": "进入 RAGFlow 知识库平台，维护资料与检索数据。",
                "icon": "FolderOpened",
                "route_type": "external",
                "route_target": settings.KNOWLEDGE_BASE_ENTRY_URL,
                "open_mode": "new_tab",
            }
        )

    if _user_has_any_permission(user, ["platform.manage"]):
        modules.append(
            {
                "module_id": "access_admin",
                "name": "组织与权限管理",
                "description": "管理用户、角色、部门与权限分配。",
                "icon": "Setting",
                "route_type": "internal",
                "route_target": "/admin/access",
                "open_mode": "same_tab",
            }
        )

    if _user_has_any_permission(user, ["audit.view"]):
        modules.append(
            {
                "module_id": "audit_center",
                "name": "审计日志中心",
                "description": "查看关键操作、访问轨迹与平台审计日志。",
                "icon": "Document",
                "route_type": "internal",
                "route_target": "/admin/audit",
                "open_mode": "same_tab",
            }
        )

    return modules


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        existing_user = User.objects.filter(username=username).first()
        if existing_user and (
            existing_user.account_status in {"inactive", "archived"} or not existing_user.is_active
        ):
            return Response({"code": 40003, "message": "账户已停用", "data": None}, status=status.HTTP_403_FORBIDDEN)
        if existing_user and existing_user.is_locked:
            return Response({"code": 40004, "message": "账户已锁定，请稍后再试", "data": None}, status=status.HTTP_423_LOCKED)

        user = authenticate(request, username=username, password=password)
        if not user:
            if existing_user:
                record_login_failure(existing_user)
            return Response({"code": 40001, "message": "用户名或密码错误", "data": None}, status=status.HTTP_400_BAD_REQUEST)

        if user.account_status in {"inactive", "archived"} or not user.is_active:
            return Response({"code": 40003, "message": "账户已停用", "data": None}, status=status.HTTP_403_FORBIDDEN)
        if user.is_locked:
            return Response({"code": 40004, "message": "账户已锁定，请稍后再试", "data": None}, status=status.HTTP_423_LOCKED)

        with transaction.atomic():
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)
            record_login_success(user, ip_address=request.META.get("REMOTE_ADDR"))
            AuditLog.objects.create(
                user=user,
                action="auth.login",
                resource_type="user",
                resource_id=str(user.id),
                detail_json={"ip": request.META.get("REMOTE_ADDR", "")},
            )

        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "token": token.key,
                    "token_type": "Token",
                    "expires_at": (token.created + timedelta(days=TOKEN_VALIDITY_DAYS)).isoformat(),
                    "expires_in_days": TOKEN_VALIDITY_DAYS,
                    "user": UserSerializer(user).data,
                },
            }
        )


class LogoutView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        AuditLog.objects.create(
            user=request.user,
            action="auth.logout",
            resource_type="user",
            resource_id=str(request.user.id),
            detail_json={},
        )
        return Response({"code": 0, "message": "ok", "data": {"logged_out": True}})


class CurrentUserView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"code": 0, "message": "ok", "data": UserSerializer(request.user).data})


class PlatformModuleListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "items": _build_platform_modules_for_user(request.user),
                },
            }
        )


class UserListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    def get(self, request):
        qs = User.objects.select_related("department").prefetch_related("user_roles__role", "user_roles__department")
        department_code = request.query_params.get("department_code")
        keyword = request.query_params.get("keyword")
        include_archived = request.query_params.get("include_archived") in {"1", "true", "True"}
        if department_code:
            qs = qs.filter(department__code=department_code)
        if keyword:
            qs = qs.filter(
                Q(username__icontains=keyword)
                | Q(display_name__icontains=keyword)
                | Q(email__icontains=keyword)
            )
        if not include_archived:
            qs = qs.exclude(account_status="archived")
        qs = qs.order_by("username")
        return Response({"code": 0, "message": "ok", "data": {"items": UserSerializer(qs[:200], many=True).data}})

    def post(self, request):
        serializer = UserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="user.create",
            resource_type="user",
            resource_id=str(user.id),
            detail_json={"username": user.username},
        )
        return Response({"code": 0, "message": "ok", "data": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    def patch(self, request, user_id: int):
        user = get_object_or_404(User.objects.select_related("department").prefetch_related("user_roles__role", "user_roles__department"), pk=user_id)
        serializer = UserWriteSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="user.update",
            resource_type="user",
            resource_id=str(user.id),
            detail_json={"username": user.username},
        )
        return Response({"code": 0, "message": "ok", "data": UserSerializer(user).data})

    def delete(self, request, user_id: int):
        user = get_object_or_404(User, pk=user_id)
        if user.is_superuser:
            return Response({"code": 40030, "message": "超级管理员不允许删除", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if user.id == request.user.id:
            return Response({"code": 40031, "message": "不能删除当前登录账号", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        user.status_before_archive = user.account_status if user.account_status != "archived" else user.status_before_archive
        user.account_status = "archived"
        user.is_active = False
        user.archived_at = timezone.now()
        user.archived_by = request.user
        user.save(update_fields=["status_before_archive", "account_status", "is_active", "archived_at", "archived_by"])
        Token.objects.filter(user=user).delete()
        AuditLog.objects.create(
            user=request.user,
            action="user.archive",
            resource_type="user",
            resource_id=str(user.id),
            detail_json={"username": user.username},
        )
        return Response({"code": 0, "message": "ok", "data": {"archived": True}})


class UserResetPasswordView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    def post(self, request, user_id: int):
        user = get_object_or_404(User, pk=user_id)
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.force_password_change = serializer.validated_data["force_password_change"]
        user.save(update_fields=["password", "force_password_change"])
        Token.objects.filter(user=user).delete()
        AuditLog.objects.create(
            user=request.user,
            action="user.reset_password",
            resource_type="user",
            resource_id=str(user.id),
            detail_json={"username": user.username, "force_password_change": user.force_password_change},
        )
        return Response({"code": 0, "message": "ok", "data": {"reset": True}})


class UserRestoreView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    def post(self, request, user_id: int):
        user = get_object_or_404(User, pk=user_id)
        if user.account_status != "archived":
            return Response({"code": 40032, "message": "当前用户不在回收站中", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        restored_status = user.status_before_archive or "inactive"
        user.account_status = restored_status
        user.is_active = restored_status == "active"
        user.archived_at = None
        user.archived_by = None
        user.status_before_archive = ""
        user.save(update_fields=["account_status", "is_active", "archived_at", "archived_by", "status_before_archive"])
        AuditLog.objects.create(
            user=request.user,
            action="user.restore",
            resource_type="user",
            resource_id=str(user.id),
            detail_json={"username": user.username, "restored_status": restored_status},
        )
        return Response({"code": 0, "message": "ok", "data": UserSerializer(user).data})


class UserActivityView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    def get(self, request, user_id: int):
        user = get_object_or_404(User, pk=user_id)
        login_qs = (
            AuditLog.objects.select_related("user")
            .filter(user=user, action__in=["auth.login", "auth.logout"])
            .order_by("-created_at")
        )
        operation_qs = (
            AuditLog.objects.select_related("user")
            .filter(resource_type="user", resource_id=str(user.id))
            .exclude(action__in=["auth.login", "auth.logout"])
            .order_by("-created_at")
        )
        conversation_qs = (
            Conversation.objects.filter(user=user)
            .order_by("-updated_at")[:20]
        )
        task_qs = (
            Task.objects.select_related("conversation", "assistant_message")
            .filter(conversation__user=user)
            .order_by("-created_at")[:20]
        )

        conversations = [
            {
                "conversation_id": str(item.id),
                "title": item.title,
                "status": item.status,
                "last_user_message": item.last_user_message,
                "last_message_at": item.last_message_at.isoformat() if item.last_message_at else None,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in conversation_qs
        ]
        tasks = [
            {
                "task_id": str(item.id),
                "conversation_id": str(item.conversation_id),
                "conversation_title": item.conversation.title,
                "status": item.status,
                "current_step": item.current_step,
                "error_message": item.error_message,
                "assistant_summary": (item.assistant_message.summary_text[:240] if item.assistant_message and item.assistant_message.summary_text else ""),
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "finished_at": item.finished_at.isoformat() if item.finished_at else None,
            }
            for item in task_qs
        ]
        return Response(
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "login_items": AuditLogSerializer(login_qs[:20], many=True).data,
                    "operation_items": AuditLogSerializer(operation_qs[:30], many=True).data,
                    "conversation_items": conversations,
                    "task_items": tasks,
                },
            }
        )


class RoleListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.has_permission_code("role.manage") or request.user.has_permission_code("user.manage")):
            raise PermissionDenied("没有访问角色列表的权限")
        qs = Role.objects.all().prefetch_related("role_permissions__permission")
        return Response({"code": 0, "message": "ok", "data": {"items": RoleSerializer(qs, many=True).data}})

    def post(self, request):
        if not (request.user.is_superuser or request.user.has_permission_code("role.manage")):
            raise PermissionDenied("没有创建角色的权限")
        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="role.create",
            resource_type="role",
            resource_id=str(role.id),
            detail_json={"code": role.code},
        )
        return Response({"code": 0, "message": "ok", "data": RoleSerializer(role).data}, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageRoles]

    def patch(self, request, role_id: int):
        role = get_object_or_404(Role.objects.prefetch_related("role_permissions__permission"), pk=role_id)
        serializer = RoleWriteSerializer(instance=role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="role.update",
            resource_type="role",
            resource_id=str(role.id),
            detail_json={"code": role.code},
        )
        return Response({"code": 0, "message": "ok", "data": RoleSerializer(role).data})

    def delete(self, request, role_id: int):
        role = get_object_or_404(Role, pk=role_id)
        if role.is_system:
            return Response({"code": 40010, "message": "系统角色不允许删除", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if role.user_roles.exists():
            return Response({"code": 40011, "message": "角色已分配给用户，无法删除", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        code = role.code
        role.delete()
        AuditLog.objects.create(
            user=request.user,
            action="role.delete",
            resource_type="role",
            resource_id=str(role_id),
            detail_json={"code": code},
        )
        return Response({"code": 0, "message": "ok", "data": {"deleted": True}})


class PermissionListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.has_permission_code("role.manage") or request.user.has_permission_code("user.manage")):
            raise PermissionDenied("没有访问权限清单的权限")
        qs = Permission.objects.all().order_by("module", "action", "code")
        return Response({"code": 0, "message": "ok", "data": {"items": PermissionSerializer(qs, many=True).data}})


class DepartmentListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.has_permission_code("department.manage") or request.user.has_permission_code("user.manage")):
            raise PermissionDenied("没有访问部门列表的权限")
        qs = Department.objects.select_related("parent")
        return Response({"code": 0, "message": "ok", "data": {"items": DepartmentSerializer(qs, many=True).data}})

    def post(self, request):
        if not (request.user.is_superuser or request.user.has_permission_code("department.manage")):
            raise PermissionDenied("没有创建部门的权限")
        serializer = DepartmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="department.create",
            resource_type="department",
            resource_id=str(department.id),
            detail_json={"code": department.code},
        )
        return Response({"code": 0, "message": "ok", "data": DepartmentSerializer(department).data}, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageDepartments]

    def patch(self, request, department_id: int):
        department = get_object_or_404(Department.objects.select_related("parent"), pk=department_id)
        serializer = DepartmentWriteSerializer(instance=department, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action="department.update",
            resource_type="department",
            resource_id=str(department.id),
            detail_json={"code": department.code},
        )
        return Response({"code": 0, "message": "ok", "data": DepartmentSerializer(department).data})

    def delete(self, request, department_id: int):
        department = get_object_or_404(Department, pk=department_id)
        if department.children.exists():
            return Response({"code": 40020, "message": "部门下仍有子部门，无法删除", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if department.users.exists():
            return Response({"code": 40021, "message": "部门下仍有关联用户，无法删除", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        code = department.code
        department.delete()
        AuditLog.objects.create(
            user=request.user,
            action="department.delete",
            resource_type="department",
            resource_id=str(department_id),
            detail_json={"code": code},
        )
        return Response({"code": 0, "message": "ok", "data": {"deleted": True}})
