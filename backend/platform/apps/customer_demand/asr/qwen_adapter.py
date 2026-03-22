from __future__ import annotations

import base64
import mimetypes
from typing import Any

import requests
from django.conf import settings

from .base import BaseAsrAdapter
from .types import AsrTranscriptResult


class QwenAsrAdapter(BaseAsrAdapter):
    provider_name = "qwen_asr"

    def __init__(self):
        self.base_url = getattr(settings, "CUSTOMER_DEMAND_QWEN_ASR_BASE_URL", "")
        self.api_key = getattr(settings, "CUSTOMER_DEMAND_QWEN_ASR_API_KEY", "")
        self.model = getattr(settings, "CUSTOMER_DEMAND_QWEN_ASR_MODEL", "qwen3-asr-flash")

    def _resolve_mime_type(self, metadata: dict[str, Any] | None) -> str:
        metadata = metadata or {}
        content_type = (metadata.get("content_type") or "").strip()
        if content_type:
            return content_type
        filename = (metadata.get("file_name") or "").strip()
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "audio/wav"

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

        if not self.api_key or not self.base_url:
            return AsrTranscriptResult(
                text="",
                raw_text="",
                review_flag=True,
                issues=["Qwen ASR 未配置，当前返回占位结果"],
                metadata={"provider": self.provider_name, "mode": "unconfigured"},
            )

        mime_type = self._resolve_mime_type(metadata)
        data_uri = f"data:{mime_type};base64,{base64.b64encode(audio_bytes).decode('utf-8')}"
        context_text = (metadata or {}).get("context_text") or (metadata or {}).get("reference_text") or ""

        messages: list[dict[str, Any]] = []
        if context_text:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "text": str(context_text),
                        }
                    ],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": data_uri,
                        },
                    }
                ],
            }
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "asr_options": {
                "enable_itn": True,
            },
        }
        if language:
            payload["asr_options"]["language"] = language

        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            return AsrTranscriptResult(
                text="",
                raw_text="",
                review_flag=True,
                issues=[f"Qwen ASR 请求失败: {exc}"],
                metadata={
                    "provider": self.provider_name,
                    "model": self.model,
                    "sample_rate": sample_rate,
                    "language": language,
                    "request_metadata": metadata or {},
                    "mime_type": mime_type,
                    "status": "request_error",
                },
            )
        except ValueError as exc:
            return AsrTranscriptResult(
                text="",
                raw_text="",
                review_flag=True,
                issues=[f"Qwen ASR 返回解析失败: {exc}"],
                metadata={
                    "provider": self.provider_name,
                    "model": self.model,
                    "status": "invalid_json",
                },
            )

        choice = ((data.get("choices") or [{}])[0]) if isinstance(data, dict) else {}
        message = choice.get("message") or {}
        content = (message.get("content") or "").strip()
        annotations = message.get("annotations") or []
        audio_info = annotations[0] if annotations else {}
        usage = data.get("usage") or {}
        seconds = usage.get("seconds")
        issues: list[str] = []
        review_flag = False
        if not content:
            review_flag = True
            issues.append("Qwen ASR 未返回有效文本")

        return AsrTranscriptResult(
            text=content,
            raw_text=content,
            review_flag=review_flag,
            issues=issues,
            metadata={
                "provider": self.provider_name,
                "model": self.model,
                "sample_rate": sample_rate,
                "language": language,
                "detected_language": audio_info.get("language") or language,
                "emotion": audio_info.get("emotion") or "",
                "mime_type": mime_type,
                "audio_seconds": seconds,
                "request_metadata": metadata or {},
                "usage": usage,
                "request_id": data.get("id"),
            },
        )

    def healthcheck(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": "configured" if self.api_key and self.base_url else "unconfigured",
            "model": self.model,
        }
