from app.config import settings

from .base import BaseLLMAdapter


class QwenAdapter(BaseLLMAdapter):
    provider = "qwen"
    api_key_env = "QWEN_API_KEY / DASHSCOPE_API_KEY"

    def chat(self, payload: dict) -> dict:
        api_key = settings.qwen_api_key
        data = self._post_chat_completion(
            api_key=api_key,
            base_url=settings.qwen_base_url,
            body={
                "model": payload.get("model", settings.qwen_default_model),
                "messages": payload.get("messages", []),
                "temperature": payload.get("temperature", 0.2),
                "max_tokens": payload.get("max_tokens", 2048),
                "stream": False,
            },
        )
        return {
            "provider": self.provider,
            "model": payload.get("model", settings.qwen_default_model),
            "content": self._extract_content(data),
            "reasoning": self._extract_reasoning(data),
            "usage": data.get("usage", {}),
            "raw": data,
        }
