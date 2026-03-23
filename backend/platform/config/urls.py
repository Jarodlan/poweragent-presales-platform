from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.configurations.urls")),
    path("api/v1/", include("apps.conversations.urls")),
    path("api/v1/", include("apps.customer_demand.urls")),
    path("api/v1/", include("apps.presales_center.urls")),
    path("api/v1/", include("apps.tasks.urls")),
]
