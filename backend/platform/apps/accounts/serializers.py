from rest_framework import serializers

from .models import Department, Permission, Role, User, UserRole


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name", "code", "status", "parent_id")


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("code", "name", "module", "action", "resource_scope", "description")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ("id", "code", "name", "description", "data_scope", "is_system", "permissions")

    def get_permissions(self, obj):
        permission_qs = Permission.objects.filter(role_permissions__role=obj).distinct().order_by("module", "action")
        return PermissionSerializer(permission_qs, many=True).data


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
            "force_password_change",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "permissions",
            "last_login",
        )

    def get_roles(self, obj):
        return UserRoleSerializer(obj.user_roles.select_related("role", "department"), many=True).data

    def get_permissions(self, obj):
        return sorted(obj.get_permission_codes())

    def get_data_scope_resolved(self, obj):
        return obj.resolve_data_scope()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
