from django.urls import path

from .views import (
    CurrentUserView,
    DepartmentDetailView,
    DepartmentListView,
    DepartmentMergeFeishuView,
    LoginView,
    LogoutView,
    PlatformModuleListView,
    PermissionListView,
    RoleDetailView,
    RoleListView,
    UserDetailView,
    UserListView,
    UserActivityView,
    UserRestoreView,
    UserMergeFeishuView,
    UserResetPasswordView,
)

urlpatterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentUserView.as_view(), name="auth-me"),
    path("platform/modules", PlatformModuleListView.as_view(), name="platform-modules"),
    path("users", UserListView.as_view(), name="user-list"),
    path("users/<int:user_id>", UserDetailView.as_view(), name="user-detail"),
    path("users/<int:user_id>/reset-password", UserResetPasswordView.as_view(), name="user-reset-password"),
    path("users/<int:user_id>/activity", UserActivityView.as_view(), name="user-activity"),
    path("users/<int:user_id>/restore", UserRestoreView.as_view(), name="user-restore"),
    path("users/<int:user_id>/merge-feishu", UserMergeFeishuView.as_view(), name="user-merge-feishu"),
    path("roles", RoleListView.as_view(), name="role-list"),
    path("roles/<int:role_id>", RoleDetailView.as_view(), name="role-detail"),
    path("permissions", PermissionListView.as_view(), name="permission-list"),
    path("departments", DepartmentListView.as_view(), name="department-list"),
    path("departments/<int:department_id>", DepartmentDetailView.as_view(), name="department-detail"),
    path("departments/<int:department_id>/merge-feishu", DepartmentMergeFeishuView.as_view(), name="department-merge-feishu"),
]
