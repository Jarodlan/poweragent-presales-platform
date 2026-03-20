from .base import BaseLLMAdapter


class MiniMaxAdapter(BaseLLMAdapter):
    provider = "minimax"

    def chat(self, payload: dict) -> dict:
        return {
            "provider": self.provider,
            "model": payload.get("model", "MiniMax-M2.7"),
            "content": "",
            "usage": {},
        }
