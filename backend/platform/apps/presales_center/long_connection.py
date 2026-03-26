from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
import logging

import lark_oapi as lark
from django.conf import settings
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger,
    P2CardActionTriggerResponse,
)

from .services import handle_feishu_personal_task_card_action


_CARD_ACTION_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="feishu-card-action")
logger = logging.getLogger(__name__)
_RUNNER_LOCK = threading.Lock()
_RUNNER_THREAD: threading.Thread | None = None


def _resolve_log_level() -> lark.LogLevel:
    level = str(getattr(settings, "FEISHU_LONG_CONNECTION_LOG_LEVEL", "INFO") or "INFO").upper()
    return {
        "DEBUG": lark.LogLevel.DEBUG,
        "INFO": lark.LogLevel.INFO,
        "WARN": lark.LogLevel.WARNING,
        "WARNING": lark.LogLevel.WARNING,
        "ERROR": lark.LogLevel.ERROR,
    }.get(level, lark.LogLevel.INFO)


def _build_callback_response(payload: dict) -> P2CardActionTriggerResponse:
    return P2CardActionTriggerResponse(payload)


class FeishuLongConnectionRunner:
    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.domain = settings.FEISHU_BASE_URL
        self.encrypt_key = settings.FEISHU_EVENT_ENCRYPT_KEY
        self.verification_token = settings.FEISHU_EVENT_VERIFICATION_TOKEN
        self.log_level = _resolve_log_level()

    def validate(self) -> None:
        missing = []
        if not self.app_id:
            missing.append("FEISHU_APP_ID")
        if not self.app_secret:
            missing.append("FEISHU_APP_SECRET")
        if not self.verification_token:
            missing.append("FEISHU_EVENT_VERIFICATION_TOKEN")
        if missing:
            raise RuntimeError(f"飞书长连接配置缺失：{', '.join(missing)}")

    def _handle_card_action_sync(self, data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
        event = data.event
        action_value = (event.action.value or {}) if event and event.action else {}
        action_name = str(action_value.get("action") or "").strip()
        logger.warning(
            "Feishu long-connection card action received: action=%s open_id=%s user_id=%s message_id=%s",
            action_name,
            str(getattr(event.operator, "open_id", "") or "").strip(),
            str(getattr(event.operator, "user_id", "") or "").strip(),
            str(getattr(getattr(event, "context", None), "open_message_id", "") or "").strip(),
        )
        if action_name != "create_personal_feishu_task":
            return _build_callback_response({"toast": {"type": "info", "content": "未识别的卡片动作。"}})

        payload = handle_feishu_personal_task_card_action(
            task_id=str(action_value.get("presales_task_id") or "").strip(),
            operator_open_id=str(getattr(event.operator, "open_id", "") or "").strip(),
            operator_user_id=str(getattr(event.operator, "user_id", "") or "").strip(),
            operator_name="",
            callback_token=str(getattr(event, "token", "") or "").strip(),
            source_message_id=str(getattr(getattr(event, "context", None), "open_message_id", "") or "").strip(),
        )
        return _build_callback_response(payload)

    def _handle_card_action(self, data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
        # The Feishu SDK expects a sync callback here, but it invokes it from an async
        # runtime. We offload ORM/database work into a worker thread and synchronously
        # wait for the result so the SDK still gets a normal response object.
        return _CARD_ACTION_EXECUTOR.submit(self._handle_card_action_sync, data).result()

    def build_client(self) -> lark.ws.Client:
        dispatcher = (
            lark.EventDispatcherHandler.builder(
                self.encrypt_key or "",
                self.verification_token,
                self.log_level,
            )
            .register_p2_card_action_trigger(self._handle_card_action)
            .build()
        )
        return lark.ws.Client(
            self.app_id,
            self.app_secret,
            log_level=self.log_level,
            event_handler=dispatcher,
            domain=self.domain,
            auto_reconnect=True,
        )

    def start_background(self) -> threading.Thread:
        self.validate()
        thread = threading.Thread(target=self.build_client().start, daemon=True, name="feishu-long-connection")
        thread.start()
        return thread

    def run_forever(self) -> None:
        self.validate()
        self.build_client().start()


def ensure_feishu_long_connection_started() -> bool:
    global _RUNNER_THREAD
    with _RUNNER_LOCK:
        if _RUNNER_THREAD and _RUNNER_THREAD.is_alive():
            return False

        runner = FeishuLongConnectionRunner()
        runner.validate()
        _RUNNER_THREAD = runner.start_background()
        logger.warning("Feishu long-connection listener auto-started with Django.")
        return True
