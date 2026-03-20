from typing import Any

import httpx


class BaseLLMAdapter:
    provider: str = "base"
    api_key_env: str = ""
    base_url: str = ""

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _require_api_key(self, api_key: str) -> None:
        if not api_key or api_key == "replace-me":
            raise RuntimeError(f"请先配置 {self.api_key_env} 环境变量，然后再调用 {self.provider} 模型。")

    def _post_chat_completion(
        self,
        *,
        api_key: str,
        base_url: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_api_key(api_key)
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return content or ""

    @staticmethod
    def _extract_reasoning(data: dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return message.get("reasoning_content", "") or message.get("reasoning", "") or ""
