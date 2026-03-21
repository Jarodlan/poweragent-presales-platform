from django.urls import path

from .views import CurrentUserView, DepartmentListView, LoginView, LogoutView, RoleListView, UserListView

urlpatterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentUserView.as_view(), name="auth-me"),
    path("users", UserListView.as_view(), name="user-list"),
    path("roles", RoleListView.as_view(), name="role-list"),
    path("departments", DepartmentListView.as_view(), name="department-list"),
]
