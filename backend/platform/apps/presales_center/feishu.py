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
    APP_TOKEN_CACHE_KEY = "presales_center:feishu_app_access_token"
    APP_TOKEN_EXPIRE_KEY = "presales_center:feishu_app_access_token_expire"

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

    def get_app_access_token(self, *, force_refresh: bool = False) -> str:
        if not self.is_configured():
            raise FeishuApiError("飞书应用未配置，请补齐 FEISHU_APP_ID / FEISHU_APP_SECRET。")

        if not force_refresh:
            cached = cache.get(self.APP_TOKEN_CACHE_KEY)
            if cached:
                return cached

        response = requests.post(
            f"{self.base_url}/open-apis/auth/v3/app_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0 or not payload.get("app_access_token"):
            raise FeishuApiError(
                payload.get("msg") or "获取飞书 app_access_token 失败",
                code=payload.get("code"),
                response_payload=payload,
            )

        token = payload["app_access_token"]
        expire_seconds = int(payload.get("expire") or 7200)
        cache.set(self.APP_TOKEN_CACHE_KEY, token, max(expire_seconds - 120, 60))
        cache.set(self.APP_TOKEN_EXPIRE_KEY, expire_seconds, max(expire_seconds - 120, 60))
        return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        use_auth: bool = True,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        elif use_auth:
            headers["Authorization"] = f"Bearer {self.get_tenant_access_token()}"

        response = requests.request(
            method=method.upper(),
            url=f"{self.base_url}/open-apis/{path.lstrip('/')}",
            params=params,
            json=json_body,
            headers=headers,
            timeout=25,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            message = payload.get("msg") or f"飞书接口请求失败（HTTP {response.status_code}）"
            if response.status_code == 403 and payload.get("code") == 91403:
                message = "飞书 CRM 当前应用缺少多维表格写入权限，或这张多维表格尚未向应用开放编辑权限。"
            raise FeishuApiError(
                message,
                code=payload.get("code") or response.status_code,
                response_payload=payload or {"http_status": response.status_code, "text": response.text},
            )
        if payload.get("code") != 0:
            raise FeishuApiError(
                payload.get("msg") or "飞书接口调用失败",
                code=payload.get("code"),
                response_payload=payload,
            )
        return payload

    def build_user_authorize_url(self, *, state: str, redirect_uri: str) -> str:
        return (
            f"{settings.FEISHU_USER_AUTH_BASE_URL.rstrip('/')}/open-apis/authen/v1/index"
            f"?app_id={self.app_id}&redirect_uri={requests.utils.quote(redirect_uri, safe='')}&state={requests.utils.quote(state, safe='')}"
        )

    def exchange_user_access_token(self, *, code: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/open-apis/authen/v1/access_token",
            json={"grant_type": "authorization_code", "code": code},
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.get_app_access_token()}",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise FeishuApiError(
                payload.get("msg") or "获取飞书用户访问凭证失败",
                code=payload.get("code"),
                response_payload=payload,
            )
        return payload

    def refresh_user_access_token(self, *, refresh_token: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/open-apis/authen/v1/refresh_access_token",
            json={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.get_app_access_token()}",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise FeishuApiError(
                payload.get("msg") or "刷新飞书用户访问凭证失败",
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

    def create_task(
        self,
        *,
        user_id_type: str,
        title: str,
        description: str,
        due_timestamp: int | None = None,
        collaborator_ids: list[str] | None = None,
        follower_ids: list[str] | None = None,
        href_url: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "summary": title,
            "description": description,
        }
        if due_timestamp:
            body["due"] = {"timestamp": str(due_timestamp)}
        if collaborator_ids:
            body["collaborator_ids"] = collaborator_ids
        if follower_ids:
            body["follower_ids"] = follower_ids
        if href_url:
            body["origin"] = {
                "platform_i18n_name": {
                    "zh_cn": "PowerAgent 售前闭环中心",
                    "en_us": "PowerAgent Presales Center",
                },
                "href": {
                    "url": href_url,
                },
            }

        return self._request(
            "POST",
            "/task/v2/tasks",
            params={"user_id_type": user_id_type},
            json_body=body,
            access_token=access_token,
        )

    def create_task_collaborator(
        self,
        *,
        task_id: str,
        user_id_type: str,
        collaborator_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/task/v1/tasks/{task_id}/collaborators",
            params={"user_id_type": user_id_type},
            json_body={"id": collaborator_id},
        )

    def create_task_follower(
        self,
        *,
        task_id: str,
        user_id_type: str,
        follower_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/task/v1/tasks/{task_id}/followers",
            params={"user_id_type": user_id_type},
            json_body={"id": follower_id},
        )

    def update_card_by_token(
        self,
        *,
        token: str,
        card: dict[str, Any],
        open_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "token": token,
            "card": card,
        }
        if open_ids:
            body["card"]["open_ids"] = open_ids
        return self._request(
            "POST",
            "/interactive/v1/card/update",
            json_body=body,
        )
