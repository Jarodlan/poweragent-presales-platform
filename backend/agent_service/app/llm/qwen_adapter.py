from .base import BaseLLMAdapter


class QwenAdapter(BaseLLMAdapter):
    provider = "qwen"

    def chat(self, payload: dict) -> dict:
        return {
            "provider": self.provider,
            "model": payload.get("model", "qwen3.5-plus"),
            "content": "",
            "usage": {},
        }
