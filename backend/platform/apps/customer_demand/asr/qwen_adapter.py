from __future__ import annotations

import base64
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

import requests
from django.conf import settings

from .base import BaseAsrAdapter
from .types import AsrTranscriptResult


class QwenAsrAdapter(BaseAsrAdapter):
    provider_name = "qwen_asr"
    _PASSTHROUGH_MIME_TYPES = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/x-m4a",
        "audio/aac",
    }

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

    def _normalize_transcript_text(self, text: str) -> str:
        normalized = (text or "").strip()
        if not normalized:
            return ""
        # 过滤掉只有标点、停顿符或极短无意义结果，避免前端出现“。”之类脏分段。
        semantic_chars = re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)
        if not semantic_chars:
            return ""
        if len(semantic_chars) <= 1:
            return ""
        if len(semantic_chars) <= 2 and semantic_chars in {"嗯", "啊", "额", "哦", "唉", "哎"}:
            return ""
        return normalized

    def _source_extension(self, mime_type: str, metadata: dict[str, Any] | None) -> str:
        metadata = metadata or {}
        filename = (metadata.get("file_name") or "").strip()
        suffix = os.path.splitext(filename)[1]
        if suffix:
            return suffix
        if "webm" in mime_type:
            return ".webm"
        if "ogg" in mime_type:
            return ".ogg"
        if "mp4" in mime_type or "m4a" in mime_type:
            return ".m4a"
        if "wav" in mime_type:
            return ".wav"
        return ".audio"

    def _prepare_audio_for_qwen(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        sample_rate: int,
        metadata: dict[str, Any] | None,
    ) -> tuple[bytes, str, dict[str, Any]]:
        payload_metadata: dict[str, Any] = {
            "source_mime_type": mime_type,
            "source_file_size": len(audio_bytes),
            "transcoded": False,
        }
        if mime_type in self._PASSTHROUGH_MIME_TYPES:
            return audio_bytes, mime_type, payload_metadata

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            payload_metadata["transcode_error"] = "ffmpeg_not_found"
            return audio_bytes, mime_type, payload_metadata

        source_extension = self._source_extension(mime_type, metadata)
        with tempfile.NamedTemporaryFile(delete=False, suffix=source_extension) as source_file:
            source_file.write(audio_bytes)
            source_path = source_file.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as target_file:
            target_path = target_file.name

        try:
            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    source_path,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    str(sample_rate),
                    "-b:a",
                    "96k",
                    target_path,
                ],
                check=True,
                capture_output=True,
                timeout=45,
            )
            with open(target_path, "rb") as result_file:
                converted_bytes = result_file.read()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            payload_metadata["transcode_error"] = str(exc)
            return audio_bytes, mime_type, payload_metadata
        finally:
            for file_path in (source_path, target_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        payload_metadata.update(
            {
                "transcoded": True,
                "target_mime_type": "audio/mpeg",
                "target_file_size": len(converted_bytes),
            }
        )
        return converted_bytes, "audio/mpeg", payload_metadata

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
        prepared_audio_bytes, prepared_mime_type, prepared_metadata = self._prepare_audio_for_qwen(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            sample_rate=sample_rate,
            metadata=metadata,
        )
        data_uri = f"data:{prepared_mime_type};base64,{base64.b64encode(prepared_audio_bytes).decode('utf-8')}"
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
                    "mime_type": prepared_mime_type,
                    "audio_prepare": prepared_metadata,
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
        normalized_content = self._normalize_transcript_text(content)
        annotations = message.get("annotations") or []
        audio_info = annotations[0] if annotations else {}
        usage = data.get("usage") or {}
        seconds = usage.get("seconds")
        issues: list[str] = []
        review_flag = False
        if not normalized_content:
            review_flag = True
            issues.append("Qwen ASR 未返回有效文本或结果仅包含无意义标点")

        return AsrTranscriptResult(
            text=normalized_content,
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
                "mime_type": prepared_mime_type,
                "source_mime_type": mime_type,
                "audio_seconds": seconds,
                "request_metadata": metadata or {},
                "audio_prepare": prepared_metadata,
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
