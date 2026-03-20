from typing import Any

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
