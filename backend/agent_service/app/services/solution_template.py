from functools import lru_cache
from pathlib import Path

from app.config import settings


DEFAULT_SECTION_TITLES = [
    "背景介绍",
    "核心挑战识别",
    "建设目标",
    "总体技术架构",
    "技术创新方向",
    "成功案例介绍",
    "技术实施方案",
    "效益分析",
    "效益评估指标",
    "总结",
]


def _read_text(path_str: str) -> str:
    path = Path(path_str)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _extract_section_titles(template_text: str) -> list[str]:
    titles: list[str] = []
    for line in template_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            titles.append(stripped[3:].strip())
    return titles


@lru_cache(maxsize=1)
def get_solution_template() -> dict[str, object]:
    enabled = settings.solution_template_enabled
    template_text = _read_text(settings.solution_template_path)
    reference_text = _read_text(settings.solution_template_source_path)
    section_titles = _extract_section_titles(template_text) or DEFAULT_SECTION_TITLES

    return {
        "enabled": enabled,
        "template_path": settings.solution_template_path,
        "source_path": settings.solution_template_source_path,
        "template_text": template_text,
        "reference_text": reference_text,
        "section_titles": section_titles,
        "template_excerpt": template_text[:5000],
        "reference_excerpt": reference_text[:3500],
    }
