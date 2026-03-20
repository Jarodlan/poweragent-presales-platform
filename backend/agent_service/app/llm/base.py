from typing import Any


class BaseLLMAdapter:
    provider: str = "base"

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
