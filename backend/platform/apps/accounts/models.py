from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Department(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Permission(models.Model):
    RESOURCE_SCOPE_CHOICES = [
        ("platform", "Platform"),
        ("department", "Department"),
        ("self", "Self"),
    ]

    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128)
    module = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    resource_scope = models.CharField(max_length=16, choices=RESOURCE_SCOPE_CHOICES, default="platform")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module", "action", "code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Role(models.Model):
    DATA_SCOPE_CHOICES = [
        ("self", "Self"),
        ("department", "Department"),
        ("all", "All"),
    ]

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    data_scope = models.CharField(max_length=16, choices=DATA_SCOPE_CHOICES, default="self")
    is_system = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    ACCOUNT_STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("locked", "Locked"),
    ]
    DATA_SCOPE_CHOICES = [
        ("self", "Self"),
        ("department", "Department"),
        ("all", "All"),
    ]

    display_name = models.CharField(max_length=128, blank=True)
    employee_no = models.CharField(max_length=64, blank=True, db_index=True)
    phone_number = models.CharField(max_length=32, blank=True)
    job_title = models.CharField(max_length=128, blank=True)
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    account_status = models.CharField(max_length=16, choices=ACCOUNT_STATUS_CHOICES, default="active")
    data_scope = models.CharField(max_length=16, choices=DATA_SCOPE_CHOICES, default="self")
    force_password_change = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta(AbstractUser.Meta):
        ordering = ["username"]

    def __str__(self) -> str:
        return self.display_name or self.username

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def get_role_codes(self) -> list[str]:
        return list(self.user_roles.select_related("role").values_list("role__code", flat=True))

    def get_permission_codes(self) -> set[str]:
        return set(
            Permission.objects.filter(role_permissions__role__user_roles__user=self)
            .values_list("code", flat=True)
            .distinct()
        )

    def has_permission_code(self, code: str) -> bool:
        return code in self.get_permission_codes()

    def resolve_data_scope(self) -> str:
        role_scope_order = {"self": 1, "department": 2, "all": 3}
        best_scope = self.data_scope or "self"
        for role_scope in self.user_roles.select_related("role").values_list("role__data_scope", flat=True):
            if role_scope_order.get(role_scope, 0) > role_scope_order.get(best_scope, 0):
                best_scope = role_scope
        return best_scope


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_roles",
    )
    assigned_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_user_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "role", "department")]
        ordering = ["user__username", "role__name"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.role}"


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("role", "permission")]
        ordering = ["role__name", "permission__code"]

    def __str__(self) -> str:
        return f"{self.role} -> {self.permission}"
