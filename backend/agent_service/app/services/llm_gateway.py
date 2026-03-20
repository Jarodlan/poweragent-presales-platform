from typing import Any

from app.config import settings
from app.llm.minimax_adapter import MiniMaxAdapter
from app.llm.qwen_adapter import QwenAdapter


class LLMGateway:
    def __init__(self) -> None:
        self.adapters = {
            "qwen": QwenAdapter(),
            "minimax": MiniMaxAdapter(),
        }

    def chat(self, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        adapter = self.adapters[provider]
        return adapter.chat(payload)

    def chat_with_fallback(self, payload: dict[str, Any]) -> dict[str, Any]:
        primary_provider = payload.get("provider", "qwen")
        fallback_provider = "minimax" if primary_provider == "qwen" else "qwen"

        try:
            return self.chat(primary_provider, payload)
        except Exception as primary_exc:
            fallback_payload = dict(payload)
            fallback_payload["provider"] = fallback_provider
            if fallback_provider == "minimax":
                fallback_payload["model"] = payload.get("fallback_model", settings.minimax_default_model)
            else:
                fallback_payload["model"] = payload.get("fallback_model", settings.qwen_default_model)
            try:
                return self.chat(fallback_provider, fallback_payload)
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"主模型调用失败: {primary_exc}; 备用模型调用失败: {fallback_exc}"
                ) from fallback_exc
