from app.config import settings

from .base import BaseLLMAdapter


class MiniMaxAdapter(BaseLLMAdapter):
    provider = "minimax"
    api_key_env = "MINIMAX_API_KEY"

    def chat(self, payload: dict) -> dict:
        api_key = settings.minimax_api_key
        data = self._post_chat_completion(
            api_key=api_key,
            base_url=settings.minimax_base_url,
            body={
                "model": payload.get("model", settings.minimax_default_model),
                "messages": payload.get("messages", []),
                "temperature": payload.get("temperature", 0.2),
                "max_tokens": payload.get("max_tokens", 2048),
                "stream": False,
            },
        )
        return {
            "provider": self.provider,
            "model": payload.get("model", settings.minimax_default_model),
            "content": self._extract_content(data),
            "reasoning": self._extract_reasoning(data),
            "usage": data.get("usage", {}),
            "raw": data,
        }
