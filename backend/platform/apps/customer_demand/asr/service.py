from __future__ import annotations

from typing import Any

from .factory import get_asr_adapter
from .types import AsrTranscriptResult


def transcribe_audio_chunk(
    *,
    audio_bytes: bytes,
    provider: str | None = None,
    sample_rate: int = 16000,
    language: str = "zh",
    metadata: dict[str, Any] | None = None,
) -> AsrTranscriptResult:
    adapter = get_asr_adapter(provider)
    return adapter.transcribe_chunk(
        audio_bytes=audio_bytes,
        sample_rate=sample_rate,
        language=language,
        metadata=metadata,
    )

