from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .types import AsrTranscriptResult


class BaseAsrAdapter(ABC):
    provider_name = "base"

    @abstractmethod
    def transcribe_chunk(
        self,
        *,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: str = "zh",
        metadata: dict[str, Any] | None = None,
    ) -> AsrTranscriptResult:
        raise NotImplementedError

    def healthcheck(self) -> dict[str, Any]:
        return {"provider": self.provider_name, "status": "unknown"}

