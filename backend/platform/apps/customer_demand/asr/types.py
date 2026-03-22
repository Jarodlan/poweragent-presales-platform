from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AsrTranscriptResult:
    text: str
    raw_text: str = ""
    confidence: float | None = None
    speaker_label: str = ""
    review_flag: bool = False
    issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

