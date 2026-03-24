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
    DepartmentMergeFeishuSerializer,
    DepartmentWriteSerializer,
    LoginSerializer,
    PermissionSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    UserMergeFeishuSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from .services import record_login_failure, record_login_success


SOLUTION_MODULE_PERMISSION_CODES = [
    "solution.access",
    "conversation.view",
    "conversation.manage_department",
    "conversation.manage_all",
    "task.view",
    "task.manage_department",
    "task.manage_all",
]

CUSTOMER_DEMAND_MODULE_PERMISSION_CODES = [
    "customer_demand.access",
    "customer_demand.view",
    "customer_demand.create",
    "customer_demand.manage_all",
    "customer_demand.export",
]

PRESALES_CENTER_PERMISSION_CODES = [
    "presales_center.access",
    "presales_task.view",
    "presales_task.manage",
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

    if _user_has_any_permission(user, PRESALES_CENTER_PERMISSION_CODES):
        modules.append(
            {
                "module_id": "presales_center",
                "name": "售前闭环中心",
                "description": "承接售前任务、飞书发送、资料归档与身份同步，打通内部协同闭环。",
                "icon": "Document",
                "route_type": "internal",
                "route_target": "/presales",
                "open_mode": "same_tab",
            }
        )

    if _user_has_any_permission(user, ["knowledge.access", "knowledge.manage"]):
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

    if _user_has_any_permission(user, ["access_admin.access", "platform.manage"]):
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

    if _user_has_any_permission(user, ["audit.access", "audit.view"]):
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


class UserMergeFeishuView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageUsers]

    @transaction.atomic
    def post(self, request, user_id: int):
        target_user = get_object_or_404(User, pk=user_id)
        serializer = UserMergeFeishuSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_user: User = serializer.validated_data["source_user"]

        if source_user.id == target_user.id:
            return Response({"code": 40041, "message": "不能将账号与自身合并", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if not (source_user.feishu_user_id or source_user.feishu_open_id):
            return Response({"code": 40042, "message": "来源账号未绑定飞书身份", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if source_user.sync_source != "feishu":
            return Response({"code": 40043, "message": "当前仅支持合并飞书同步账号", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if source_user.is_superuser:
            return Response({"code": 40044, "message": "不允许合并超级管理员账号", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if target_user.is_archived or source_user.is_archived:
            return Response({"code": 40045, "message": "归档账号不支持执行合并", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if target_user.feishu_user_id and target_user.feishu_user_id != source_user.feishu_user_id:
            return Response({"code": 40046, "message": "目标账号已绑定其他飞书用户", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if target_user.feishu_open_id and target_user.feishu_open_id != source_user.feishu_open_id:
            return Response({"code": 40047, "message": "目标账号已绑定其他飞书 open_id", "data": None}, status=status.HTTP_400_BAD_REQUEST)

        blocking_counts = {
            "conversations": source_user.conversations.count(),
            "customer_demand_sessions": source_user.customer_demand_sessions.count(),
            "owned_presales_tasks": source_user.owned_presales_tasks.count(),
            "assigned_presales_tasks": source_user.assigned_presales_tasks.count(),
            "created_presales_tasks": source_user.created_presales_tasks.count(),
            "user_roles": source_user.user_roles.count(),
        }
        if any(blocking_counts.values()):
            return Response(
                {
                    "code": 40048,
                    "message": "来源飞书账号已有业务数据，当前仅支持合并未沉淀业务数据的飞书同步账号",
                    "data": {"blocking_counts": blocking_counts},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        feishu_name = source_user.display_name or source_user.username
        target_base_name = target_user.display_name or target_user.username
        source_feishu_user_id = source_user.feishu_user_id
        source_feishu_open_id = source_user.feishu_open_id
        source_feishu_union_id = source_user.feishu_union_id
        source_last_external_status = source_user.last_external_status

        source_user.feishu_user_id = None
        source_user.feishu_open_id = None
        source_user.feishu_union_id = ""
        source_user.sync_status = "disabled"
        source_user.last_external_status = "merged"
        source_user.last_synced_at = timezone.now()
        source_user.save(
            update_fields=[
                "feishu_user_id",
                "feishu_open_id",
                "feishu_union_id",
                "sync_status",
                "last_external_status",
                "last_synced_at",
            ]
        )

        if feishu_name and feishu_name != target_base_name and f"飞书名：{feishu_name}" not in target_base_name:
            target_user.display_name = f"{target_base_name}（飞书名：{feishu_name}）"

        target_user.feishu_user_id = source_feishu_user_id or target_user.feishu_user_id
        target_user.feishu_open_id = source_feishu_open_id or target_user.feishu_open_id
        target_user.feishu_union_id = source_feishu_union_id or target_user.feishu_union_id
        target_user.sync_status = "synced"
        target_user.last_synced_at = timezone.now()
        target_user.last_external_status = source_last_external_status or target_user.last_external_status
        if not target_user.department and source_user.department:
            target_user.department = source_user.department
        if not target_user.phone_number and source_user.phone_number:
            target_user.phone_number = source_user.phone_number
        if not target_user.email and source_user.email:
            target_user.email = source_user.email
        if source_user.employee_no and not target_user.employee_no:
            target_user.employee_no = source_user.employee_no
        target_user.save()

        source_user.status_before_archive = source_user.account_status if source_user.account_status != "archived" else source_user.status_before_archive
        source_user.account_status = "archived"
        source_user.is_active = False
        source_user.archived_at = timezone.now()
        source_user.archived_by = request.user
        source_user.remarks = "\n".join(filter(None, [source_user.remarks, f"已合并到平台账号：{target_user.username}"]))
        source_user.save(
            update_fields=[
                "status_before_archive",
                "account_status",
                "is_active",
                "archived_at",
                "archived_by",
                "remarks",
            ]
        )

        AuditLog.objects.create(
            user=request.user,
            action="user.merge_feishu",
            resource_type="user",
            resource_id=str(target_user.id),
            detail_json={
                "target_username": target_user.username,
                "source_username": source_user.username,
                "source_user_id": source_user.id,
                "feishu_user_id": target_user.feishu_user_id,
            },
        )
        return Response({"code": 0, "message": "ok", "data": UserSerializer(target_user).data})


class DepartmentMergeFeishuView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [CanManageDepartments]

    @transaction.atomic
    def post(self, request, department_id: int):
        from apps.customer_demand.models import CustomerDemandSession
        from apps.presales_center.models import PresalesTask

        target_department = get_object_or_404(Department, pk=department_id)
        serializer = DepartmentMergeFeishuSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_department: Department = serializer.validated_data["source_department"]

        if source_department.id == target_department.id:
            return Response({"code": 40061, "message": "不能将部门与自身合并", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if not source_department.feishu_department_id:
            return Response({"code": 40062, "message": "来源部门未绑定飞书部门", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if source_department.sync_source != "feishu":
            return Response({"code": 40063, "message": "当前仅支持合并飞书同步部门", "data": None}, status=status.HTTP_400_BAD_REQUEST)
        if target_department.feishu_department_id and target_department.feishu_department_id != source_department.feishu_department_id:
            return Response({"code": 40064, "message": "目标部门已绑定其他飞书部门", "data": None}, status=status.HTTP_400_BAD_REQUEST)

        source_ancestor_ids: set[int] = set()
        current = source_department.parent
        while current:
            source_ancestor_ids.add(current.id)
            current = current.parent

        target_ancestor_ids: set[int] = set()
        current = target_department.parent
        while current:
            target_ancestor_ids.add(current.id)
            current = current.parent

        if source_department.id in target_ancestor_ids or target_department.id in source_ancestor_ids:
            return Response(
                {"code": 40065, "message": "暂不支持合并存在父子层级关系的部门，请选择平级部门执行合并", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_feishu_department_id = source_department.feishu_department_id
        source_department.feishu_department_id = None
        source_department.last_synced_at = timezone.now()
        source_department.save(update_fields=["feishu_department_id", "last_synced_at", "updated_at"])

        target_department.feishu_department_id = source_feishu_department_id
        target_department.last_synced_at = timezone.now()
        if not target_department.description and source_department.description:
            target_department.description = source_department.description
        target_department.save(update_fields=["feishu_department_id", "last_synced_at", "description", "updated_at"])

        User.objects.filter(department=source_department).update(department=target_department)
        CustomerDemandSession.objects.filter(department=source_department).update(department=target_department)
        PresalesTask.objects.filter(owner_department=source_department).update(owner_department=target_department)
        Department.objects.filter(parent=source_department).exclude(pk=target_department.pk).update(parent=target_department)

        user_roles = target_department.user_roles.model.objects.filter(department=source_department).select_related("user", "role")
        for item in user_roles:
            duplicate_exists = item.__class__.objects.filter(
                user=item.user,
                role=item.role,
                department=target_department,
            ).exclude(pk=item.pk).exists()
            if duplicate_exists:
                item.delete()
            else:
                item.department = target_department
                item.save(update_fields=["department"])

        source_name = source_department.name
        source_code = source_department.code
        source_department.delete()

        AuditLog.objects.create(
            user=request.user,
            action="department.merge_feishu",
            resource_type="department",
            resource_id=str(target_department.id),
            detail_json={
                "target_department": target_department.name,
                "source_department": source_name,
                "source_department_code": source_code,
                "feishu_department_id": source_feishu_department_id,
            },
        )
        return Response({"code": 0, "message": "ok", "data": DepartmentSerializer(target_department).data})


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
