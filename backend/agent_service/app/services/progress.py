from typing import Any


STEP_PROGRESS_MAP: dict[str, dict[str, Any]] = {
    "queued": {"label": "任务排队中", "progress": 2},
    "workflow_started": {"label": "工作流已启动", "progress": 5},
    "intent_identify": {"label": "意图识别中", "progress": 12},
    "intent_identify_completed": {"label": "意图识别完成", "progress": 18},
    "normalize_context": {"label": "场景参数整理中", "progress": 22},
    "normalize_context_completed": {"label": "场景参数整理完成", "progress": 28},
    "retrieve_documents": {"label": "知识检索中", "progress": 38},
    "retrieve_documents_completed": {"label": "知识检索完成", "progress": 46},
    "merge_evidence": {"label": "证据整理中", "progress": 56},
    "merge_evidence_completed": {"label": "证据整理完成", "progress": 64},
    "generate_outline": {"label": "方案大纲生成中", "progress": 74},
    "generate_outline_completed": {"label": "方案大纲生成完成", "progress": 80},
    "expand_sections": {"label": "解决方案正文生成中", "progress": 88},
    "expand_sections_completed": {"label": "解决方案正文生成完成", "progress": 92},
    "generate_implementation_section": {"label": "技术实施方案生成中", "progress": 90},
    "generate_implementation_section_completed": {"label": "技术实施方案生成完成", "progress": 91},
    "generate_kpi_section": {"label": "KPI指标表生成中", "progress": 92},
    "generate_kpi_section_completed": {"label": "KPI指标表生成完成", "progress": 93},
    "generate_summary_section": {"label": "总结章节生成中", "progress": 94},
    "generate_summary_section_completed": {"label": "总结章节生成完成", "progress": 95},
    "review_solution": {"label": "方案校核中", "progress": 96},
    "review_solution_completed": {"label": "方案校核完成", "progress": 98},
    "finalize_output": {"label": "结果整理完成", "progress": 100},
    "failed": {"label": "执行失败", "progress": 100},
    "completed": {"label": "执行完成", "progress": 100},
    "cancelled": {"label": "任务已取消", "progress": 100},
}


def describe_step(step: str, status: str = "running") -> dict[str, Any]:
    detail = STEP_PROGRESS_MAP.get(step)
    if detail:
        return {
            "step": step,
            "label": detail["label"],
            "progress": detail["progress"],
        }
    if step.startswith("generate_section:"):
        section_title = step.split(":", 1)[1]
        return {
            "step": step,
            "label": f"章节生成中：{section_title}",
            "progress": 82,
        }
    if step.startswith("generate_section_completed:"):
        section_title = step.split(":", 1)[1]
        return {
            "step": step,
            "label": f"章节生成完成：{section_title}",
            "progress": 90,
        }
    if step == "assemble_solution":
        return {
            "step": step,
            "label": "章节拼装中",
            "progress": 94,
        }
    if step == "assemble_solution_completed":
        return {
            "step": step,
            "label": "章节拼装完成",
            "progress": 95,
        }
    fallback_label = "执行完成" if status == "completed" else "正在执行工作流"
    fallback_progress = 100 if status == "completed" else 10
    return {
        "step": step or status or "running",
        "label": fallback_label,
        "progress": fallback_progress,
    }
