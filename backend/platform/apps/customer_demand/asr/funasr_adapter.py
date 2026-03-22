from __future__ import annotations

from typing import Any

from django.conf import settings

from .base import BaseAsrAdapter
from .types import AsrTranscriptResult


class FunAsrAdapter(BaseAsrAdapter):
    provider_name = "funasr"

    def __init__(self):
        self.base_url = getattr(settings, "CUSTOMER_DEMAND_FUNASR_BASE_URL", "")
        self.mode = getattr(settings, "CUSTOMER_DEMAND_FUNASR_MODE", "2pass")

    def transcribe_chunk(
        self,
        *,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: str = "zh",
        metadata: dict[str, Any] | None = None,
    ) -> AsrTranscriptResult:
        if not audio_bytes:
            return AsrTranscriptResult(text="", raw_text="", review_flag=True, issues=["空音频分片"])

        if not self.base_url:
            return AsrTranscriptResult(
                text="",
                raw_text="",
                review_flag=True,
                issues=["FunASR 未配置，当前返回占位结果"],
                metadata={"provider": self.provider_name, "mode": "unconfigured"},
            )

        # 当前阶段先定义接口与配置边界，真实 ws / 2pass 协议在下一步接入。
        return AsrTranscriptResult(
            text="",
            raw_text="",
            review_flag=True,
            issues=["FunASR 实时接入待实现"],
            metadata={
                "provider": self.provider_name,
                "mode": self.mode,
                "sample_rate": sample_rate,
                "language": language,
                "request_metadata": metadata or {},
            },
        )

    def healthcheck(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": "configured" if self.base_url else "unconfigured",
            "mode": self.mode,
        }

