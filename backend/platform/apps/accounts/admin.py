from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, Permission, Role, RolePermission, User, UserRole


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent", "status", "sort_order")
    search_fields = ("name", "code")
    list_filter = ("status",)


class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = "user"
    extra = 0
    autocomplete_fields = ("role", "department", "assigned_by")


@admin.register(User)
class PowerAgentUserAdmin(UserAdmin):
    list_display = (
        "username",
        "display_name",
        "department",
        "job_title",
        "account_status",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("account_status", "department", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "display_name", "email", "employee_no", "phone_number")
    autocomplete_fields = ("department",)
    inlines = [UserRoleInline]
    fieldsets = UserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "display_name",
                    "employee_no",
                    "phone_number",
                    "job_title",
                    "department",
                    "remarks",
                )
            },
        ),
        (
            "Account Governance",
            {
                "fields": (
                    "account_status",
                    "data_scope",
                    "force_password_change",
                    "password_changed_at",
                    "failed_login_attempts",
                    "locked_until",
                    "last_login_ip",
                )
            },
        ),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "action", "resource_scope")
    search_fields = ("code", "name", "module", "action")
    list_filter = ("module", "resource_scope")


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ("permission",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "data_scope", "is_system")
    search_fields = ("code", "name")
    list_filter = ("data_scope", "is_system")
    inlines = [RolePermissionInline]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "assigned_by", "assigned_at")
    autocomplete_fields = ("user", "role", "department", "assigned_by")
    search_fields = ("user__username", "user__display_name", "role__code", "role__name")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "created_at")
    autocomplete_fields = ("role", "permission")
    search_fields = ("role__code", "role__name", "permission__code", "permission__name")
