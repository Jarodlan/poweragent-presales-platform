from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticValidationResult:
    decision: str
    score: float | None = None
    normalized_text: str = ""
    issues: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
