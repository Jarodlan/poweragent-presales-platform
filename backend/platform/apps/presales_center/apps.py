import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings


logger = logging.getLogger(__name__)


class PresalesCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.presales_center"

    def ready(self):
        if not getattr(settings, "FEISHU_LONG_CONNECTION_AUTO_START", False):
            return

        command = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
        allowed_commands = {"runserver", "gunicorn", "uvicorn", "daphne"}
        if command and command not in allowed_commands:
            return

        # Avoid duplicate startup under Django's autoreloader parent process.
        if command == "runserver" and os.environ.get("RUN_MAIN") == "false":
            return

        try:
            from .long_connection import ensure_feishu_long_connection_started

            started = ensure_feishu_long_connection_started()
            if started:
                print("Feishu long connection auto-started with Django.")
        except Exception as exc:  # pragma: no cover - startup safety log
            logger.warning("Failed to auto-start Feishu long connection: %s", exc)
