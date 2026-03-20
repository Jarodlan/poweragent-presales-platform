from django.urls import path

from .views import MetaOptionsView


urlpatterns = [
    path("meta/options", MetaOptionsView.as_view(), name="meta-options"),
]
