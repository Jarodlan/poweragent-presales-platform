from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog

from .models import Department, Role, User
from .permissions import CanManageDepartments, CanManageRoles, CanManageUsers
from .serializers import DepartmentSerializer, LoginSerializer, RoleSerializer, UserSerializer
from .services import record_login_failure, record_login_success


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        existing_user = User.objects.filter(username=username).first()
        if existing_user and (existing_user.account_status == "inactive" or not existing_user.is_active):
            return Response({"code": 40003, "message": "账户已停用", "data": None}, status=status.HTTP_403_FORBIDDEN)
        if existing_user and existing_user.is_locked:
            return Response({"code": 40004, "message": "账户已锁定，请稍后再试", "data": None}, status=status.HTTP_423_LOCKED)

        user = authenticate(request, username=username, password=password)
        if not user:
            if existing_user:
                record_login_failure(existing_user)
            return Response({"code": 40001, "message": "用户名或密码错误", "data": None}, status=status.HTTP_400_BAD_REQUEST)

        if user.account_status == "inactive" or not user.is_active:
            return Response({"code": 40003, "message": "账户已停用", "data": None}, status=status.HTTP_403_FORBIDDEN)
        if user.is_locked:
            return Response({"code": 40004, "message": "账户已锁定，请稍后再试", "data": None}, status=status.HTTP_423_LOCKED)

        with transaction.atomic():
            token, _ = Token.objects.get_or_create(user=user)
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
                    "user": UserSerializer(user).data,
                },
            }
        )


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"code": 0, "message": "ok", "data": UserSerializer(request.user).data})


class UserListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanManageUsers]

    def get(self, request):
        qs = User.objects.select_related("department").prefetch_related("user_roles__role", "user_roles__department")
        department_code = request.query_params.get("department_code")
        if department_code:
            qs = qs.filter(department__code=department_code)
        return Response({"code": 0, "message": "ok", "data": {"items": UserSerializer(qs[:100], many=True).data}})


class RoleListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanManageRoles]

    def get(self, request):
        qs = Role.objects.all().prefetch_related("role_permissions__permission")
        return Response({"code": 0, "message": "ok", "data": {"items": RoleSerializer(qs, many=True).data}})


class DepartmentListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanManageDepartments]

    def get(self, request):
        qs = Department.objects.select_related("parent")
        return Response({"code": 0, "message": "ok", "data": {"items": DepartmentSerializer(qs, many=True).data}})
