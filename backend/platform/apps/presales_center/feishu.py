from __future__ import annotations

import json
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache


class FeishuApiError(RuntimeError):
    def __init__(self, message: str, *, code: int | None = None, response_payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.response_payload = response_payload or {}


class FeishuClient:
    TOKEN_CACHE_KEY = "presales_center:feishu_tenant_access_token"
    TOKEN_EXPIRE_KEY = "presales_center:feishu_tenant_access_token_expire"

    def __init__(self, *, base_url: str | None = None, app_id: str | None = None, app_secret: str | None = None):
        self.base_url = (base_url or settings.FEISHU_BASE_URL).rstrip("/")
        self.app_id = app_id or settings.FEISHU_APP_ID
        self.app_secret = app_secret or settings.FEISHU_APP_SECRET

    def is_configured(self) -> bool:
        return bool(self.base_url and self.app_id and self.app_secret)

    def get_tenant_access_token(self, *, force_refresh: bool = False) -> str:
        if not self.is_configured():
            raise FeishuApiError("飞书应用未配置，请补齐 FEISHU_APP_ID / FEISHU_APP_SECRET。")

        if not force_refresh:
            cached = cache.get(self.TOKEN_CACHE_KEY)
            if cached:
                return cached

        response = requests.post(
            f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0 or not payload.get("tenant_access_token"):
            raise FeishuApiError(
                payload.get("msg") or "获取飞书 tenant_access_token 失败",
                code=payload.get("code"),
                response_payload=payload,
            )

        token = payload["tenant_access_token"]
        expire_seconds = int(payload.get("expire") or 7200)
        cache.set(self.TOKEN_CACHE_KEY, token, max(expire_seconds - 120, 60))
        cache.set(self.TOKEN_EXPIRE_KEY, expire_seconds, max(expire_seconds - 120, 60))
        return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        use_auth: bool = True,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if use_auth:
            headers["Authorization"] = f"Bearer {self.get_tenant_access_token()}"

        response = requests.request(
            method=method.upper(),
            url=f"{self.base_url}/open-apis/{path.lstrip('/')}",
            params=params,
            json=json_body,
            headers=headers,
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise FeishuApiError(
                payload.get("msg") or "飞书接口调用失败",
                code=payload.get("code"),
                response_payload=payload,
            )
        return payload

    def send_message(
        self,
        *,
        receive_id: str,
        receive_id_type: str,
        message_type: str,
        message_payload: dict[str, Any],
    ) -> dict[str, Any]:
        api_message_type = "interactive" if message_type == "interactive_card" else message_type
        if message_type == "text":
            text = (
                message_payload.get("text")
                or "\n".join(part for part in [message_payload.get("title"), message_payload.get("summary")] if part)
                or "新的售前协同消息"
            )
            content = json.dumps({"text": text}, ensure_ascii=False)
        else:
            content = json.dumps(message_payload, ensure_ascii=False)

        return self._request(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            json_body={
                "receive_id": receive_id,
                "msg_type": api_message_type,
                "content": content,
            },
        )

    def list_department_children(
        self,
        *,
        department_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "user_id_type": "open_id",
            "department_id_type": "open_department_id",
            "page_size": page_size,
        }
        if page_token:
            params["page_token"] = page_token
        return self._request(
            "GET",
            f"/contact/v3/departments/{department_id}/children",
            params=params,
        )

    def list_department_users(
        self,
        *,
        department_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "user_id_type": "open_id",
            "department_id_type": "open_department_id",
            "department_id": department_id,
            "page_size": page_size,
        }
        if page_token:
            params["page_token"] = page_token
        return self._request(
            "GET",
            "/contact/v3/users/find_by_department",
            params=params,
        )

    def list_chats(
        self,
        *,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        return self._request(
            "GET",
            "/im/v1/chats",
            params=params,
        )
