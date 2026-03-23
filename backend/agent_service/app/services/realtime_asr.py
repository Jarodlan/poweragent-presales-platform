from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any

from dashscope.audio.qwen_omni import AudioFormat, MultiModality, OmniRealtimeCallback, OmniRealtimeConversation
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams

from app.config import settings


class RealtimeAsrCallback(OmniRealtimeCallback):
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.loop = loop
        self.queue = queue

    def _push(self, payload: dict[str, Any]) -> None:
        asyncio.run_coroutine_threadsafe(self.queue.put(payload), self.loop)

    def on_open(self) -> None:
        self._push({"type": "connection.open"})

    def on_close(self, close_status_code, close_msg) -> None:
        self._push(
            {
                "type": "connection.close",
                "code": close_status_code,
                "message": str(close_msg or ""),
            }
        )

    def on_event(self, response: dict[str, Any]) -> None:
        event_type = response.get("type") or ""
        if event_type == "session.created":
            self._push({"type": "session.created", "session_id": response.get("session", {}).get("id", "")})
            return
        if event_type == "session.updated":
            self._push({"type": "session.updated"})
            return
        if event_type == "conversation.item.input_audio_transcription.text":
            stash = (response.get("stash") or "").strip()
            if stash:
                self._push({"type": "transcript.partial", "text": stash})
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            transcript = (response.get("transcript") or "").strip()
            if transcript:
                self._push({"type": "transcript.final", "text": transcript})
            return
        if event_type == "input_audio_buffer.speech_started":
            self._push({"type": "speech.started"})
            return
        if event_type == "input_audio_buffer.speech_stopped":
            self._push({"type": "speech.stopped"})
            return
        if event_type == "session.finished":
            self._push({"type": "session.finished"})
            return
        if event_type == "error":
            self._push(
                {
                    "type": "error",
                    "message": str(response.get("message") or response.get("error") or "Qwen realtime ASR error"),
                    "details": response,
                }
            )


def _guess_suffix(mime_type: str) -> str:
    if "webm" in mime_type:
        return ".webm"
    if "ogg" in mime_type:
        return ".ogg"
    if "mp4" in mime_type or "m4a" in mime_type:
        return ".m4a"
    if "wav" in mime_type:
        return ".wav"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return ".mp3"
    return ".audio"


def decode_media_chunk_to_pcm16(audio_bytes: bytes, mime_type: str, sample_rate: int = 16000) -> bytes:
    if not audio_bytes:
        return b""
    if mime_type in {"audio/pcm16", "audio/raw", "audio/s16le"}:
        return audio_bytes

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("未找到 ffmpeg，无法解码实时音频分片")

    suffix = _guess_suffix(mime_type)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as source_file:
        source_file.write(audio_bytes)
        source_path = source_file.name

    try:
        result = subprocess.run(
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
                "-f",
                "s16le",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return result.stdout
    finally:
        try:
            os.remove(source_path)
        except OSError:
            pass


@dataclass
class QwenRealtimeAsrBridge:
    language: str = "zh"
    sample_rate: int = 16000
    corpus_text: str = ""

    def __post_init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.callback = RealtimeAsrCallback(self.loop, self.event_queue)
        self.conversation = OmniRealtimeConversation(
            model=settings.qwen_realtime_asr_model,
            url=settings.qwen_realtime_asr_url,
            api_key=settings.qwen_api_key,
            callback=self.callback,
        )

    async def connect(self) -> None:
        await asyncio.to_thread(self.conversation.connect)
        transcription_params = TranscriptionParams(
            language=self.language,
            sample_rate=self.sample_rate,
            input_audio_format="pcm",
            corpus_text=self.corpus_text or None,
        )
        await asyncio.to_thread(
            self.conversation.update_session,
            [MultiModality.TEXT],
            None,
            AudioFormat.PCM_16000HZ_MONO_16BIT,
            AudioFormat.PCM_16000HZ_MONO_16BIT,
            True,
            None,
            True,
            "server_vad",
            300,
            0.0,
            450,
            None,
            None,
            transcription_params,
        )

    async def append_media_chunk(self, audio_bytes: bytes, mime_type: str) -> None:
        pcm_bytes = await asyncio.to_thread(decode_media_chunk_to_pcm16, audio_bytes, mime_type, self.sample_rate)
        if not pcm_bytes:
            return
        await asyncio.to_thread(self.conversation.append_audio, base64.b64encode(pcm_bytes).decode("utf-8"))

    async def finish(self) -> None:
        await asyncio.to_thread(self.conversation.end_session, 20)

    async def close(self) -> None:
        await asyncio.to_thread(self.conversation.close)


def parse_ws_message(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("无效的 WebSocket JSON 消息") from exc
    if not isinstance(payload, dict):
        raise ValueError("WebSocket 消息必须是对象")
    return payload
