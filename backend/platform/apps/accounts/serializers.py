from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from .models import Department, Permission, Role, User, UserRole


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "description",
            "status",
            "parent_id",
            "parent_name",
            "sort_order",
            "created_at",
            "updated_at",
        )


class DepartmentWriteSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Department
        fields = ("name", "code", "description", "status", "parent_id", "sort_order")

    def validate_code(self, value: str):
        qs = Department.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("部门编码已存在")
        return value


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("code", "name", "module", "action", "resource_scope", "description")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "code",
            "name",
            "description",
            "data_scope",
            "is_system",
            "permissions",
            "created_at",
            "updated_at",
        )

    def get_permissions(self, obj):
        permission_qs = Permission.objects.filter(role_permissions__role=obj).distinct().order_by("module", "action")
        return PermissionSerializer(permission_qs, many=True).data


class RoleWriteSerializer(serializers.ModelSerializer):
    permission_codes = serializers.ListField(child=serializers.CharField(), allow_empty=True, write_only=True)

    class Meta:
        model = Role
        fields = ("code", "name", "description", "data_scope", "permission_codes")

    def validate_code(self, value: str):
        qs = Role.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("角色编码已存在")
        if self.instance and self.instance.is_system and value != self.instance.code:
            raise serializers.ValidationError("系统角色不允许修改编码")
        return value

    def validate_permission_codes(self, value: list[str]):
        normalized = sorted(set(value))
        existing = set(Permission.objects.filter(code__in=normalized).values_list("code", flat=True))
        missing = sorted(set(normalized) - existing)
        if missing:
            raise serializers.ValidationError(f"存在未识别的权限编码: {', '.join(missing)}")
        return normalized

    @transaction.atomic
    def create(self, validated_data):
        permission_codes = validated_data.pop("permission_codes", [])
        role = Role.objects.create(is_system=False, **validated_data)
        self._sync_permissions(role, permission_codes)
        return role

    @transaction.atomic
    def update(self, instance, validated_data):
        permission_codes = validated_data.pop("permission_codes", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=[*validated_data.keys(), "updated_at"] if validated_data else None)
        if permission_codes is not None:
            self._sync_permissions(instance, permission_codes)
        return instance

    def _sync_permissions(self, role: Role, permission_codes: list[str]):
        permissions = list(Permission.objects.filter(code__in=permission_codes))
        role.role_permissions.exclude(permission__code__in=permission_codes).delete()
        existing_codes = set(role.role_permissions.values_list("permission__code", flat=True))
        for permission in permissions:
            if permission.code in existing_codes:
                continue
            role.role_permissions.create(permission=permission)


class UserRoleSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = UserRole
        fields = ("id", "role", "department", "assigned_at")


class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    data_scope_resolved = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "display_name",
            "employee_no",
            "phone_number",
            "job_title",
            "department",
            "account_status",
            "data_scope",
            "data_scope_resolved",
            "feishu_user_id",
            "feishu_open_id",
            "sync_source",
            "sync_status",
            "force_password_change",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "permissions",
            "last_login",
            "last_login_ip",
            "remarks",
            "archived_at",
            "status_before_archive",
            "date_joined",
        )

    def get_roles(self, obj):
        return UserRoleSerializer(obj.user_roles.select_related("role", "department"), many=True).data

    def get_permissions(self, obj):
        return sorted(obj.get_permission_codes())

    def get_data_scope_resolved(self, obj):
        return obj.resolve_data_scope()


class UserWriteSerializer(serializers.ModelSerializer):
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )
    role_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        required=False,
        write_only=True,
    )
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "display_name",
            "employee_no",
            "phone_number",
            "job_title",
            "department_id",
            "account_status",
            "data_scope",
            "force_password_change",
            "is_active",
            "is_staff",
            "remarks",
            "password",
            "role_ids",
        )

    def validate_username(self, value: str):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate_role_ids(self, value: list[int]):
        normalized = sorted(set(value))
        existing = set(Role.objects.filter(id__in=normalized).values_list("id", flat=True))
        missing = sorted(set(normalized) - existing)
        if missing:
            raise serializers.ValidationError(f"存在未识别的角色ID: {', '.join(str(item) for item in missing)}")
        return normalized

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "创建用户时必须设置初始密码"})
        password = attrs.get("password")
        if password and len(password) < 8:
            raise serializers.ValidationError({"password": "密码长度至少为 8 位"})
        account_status = attrs.get("account_status")
        if account_status == "inactive":
            attrs["is_active"] = False
        elif account_status == "active":
            attrs["is_active"] = True
        elif account_status == "archived":
            attrs["is_active"] = False
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        role_ids = validated_data.pop("role_ids", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        self._sync_roles(user, role_ids)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        role_ids = validated_data.pop("role_ids", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
            instance.force_password_change = False
        instance.save()
        if role_ids is not None:
            self._sync_roles(instance, role_ids)
        else:
            self._sync_role_departments(instance)
        return instance

    def _sync_roles(self, user: User, role_ids: list[int]):
        roles = list(Role.objects.filter(id__in=role_ids))
        user.user_roles.exclude(role_id__in=role_ids).delete()
        existing_ids = set(user.user_roles.values_list("role_id", flat=True))
        for role in roles:
            if role.id in existing_ids:
                continue
            UserRole.objects.create(user=user, role=role, department=user.department)
        self._sync_role_departments(user)

    def _sync_role_departments(self, user: User):
        user.user_roles.update(department=user.department)


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    force_password_change = serializers.BooleanField(default=True)

    def validate_password(self, value: str):
        if len(value) < 8:
            raise serializers.ValidationError("密码长度至少为 8 位")
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
