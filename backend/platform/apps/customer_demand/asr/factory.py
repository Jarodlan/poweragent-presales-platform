from __future__ import annotations

from django.conf import settings

from .base import BaseAsrAdapter
from .funasr_adapter import FunAsrAdapter
from .qwen_adapter import QwenAsrAdapter


def get_asr_adapter(provider: str | None = None) -> BaseAsrAdapter:
    selected = (provider or getattr(settings, "CUSTOMER_DEMAND_ASR_PROVIDER", "qwen")).lower()
    if selected == "funasr":
        return FunAsrAdapter()
    return QwenAsrAdapter()

