from django.urls import path

from .views import TaskCancelView, TaskResultView, TaskStreamView


urlpatterns = [
    path("solution/tasks/<uuid:task_id>", TaskResultView.as_view(), name="task-result"),
    path("solution/tasks/<uuid:task_id>/stream", TaskStreamView.as_view(), name="task-stream"),
    path("solution/tasks/<uuid:task_id>/cancel", TaskCancelView.as_view(), name="task-cancel"),
]
