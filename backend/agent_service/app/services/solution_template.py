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


SCENARIO_TEMPLATE_MAP = {
    "fault_diagnosis_solution": {
        "document_title": "智能配电网故障诊断解决方案",
        "template_path": settings.solution_template_path,
        "source_path": settings.solution_template_source_path,
    },
    "storage_aggregation_solution": {
        "document_title": "分布式储能聚合运营智能体解决方案",
        "template_path": settings.storage_solution_template_path,
        "source_path": settings.storage_solution_template_source_path,
    },
}


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


def _extract_template_block(template_text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = template_text.find(marker)
    if start == -1:
        return ""
    remaining = template_text[start:].splitlines()
    collected: list[str] = []
    for idx, line in enumerate(remaining):
        if idx > 0 and line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def infer_template_key(query: str = "", intent: str = "") -> str:
    normalized = f"{intent} {query}".lower()
    storage_keywords = [
        "储能",
        "聚合",
        "虚拟电厂",
        "电价",
        "现货",
        "需求响应",
        "aggregator",
        "storage",
    ]
    if any(keyword in normalized for keyword in storage_keywords):
        return "storage_aggregation_solution"
    return "fault_diagnosis_solution"


@lru_cache(maxsize=8)
def get_solution_template(template_key: str = "fault_diagnosis_solution") -> dict[str, object]:
    enabled = settings.solution_template_enabled
    template_meta = SCENARIO_TEMPLATE_MAP.get(template_key, SCENARIO_TEMPLATE_MAP["fault_diagnosis_solution"])
    template_text = _read_text(str(template_meta["template_path"]))
    reference_text = _read_text(str(template_meta["source_path"]))
    section_titles = _extract_section_titles(template_text) or DEFAULT_SECTION_TITLES
    section_blocks = {
        title: _extract_template_block(template_text, title)
        for title in section_titles
    }

    return {
        "enabled": enabled,
        "template_key": template_key,
        "document_title": template_meta["document_title"],
        "template_path": str(template_meta["template_path"]),
        "source_path": str(template_meta["source_path"]),
        "template_text": template_text,
        "reference_text": reference_text,
        "section_titles": section_titles,
        "section_blocks": section_blocks,
        "template_excerpt": template_text[:5000],
        "reference_excerpt": reference_text[:3500],
    }
