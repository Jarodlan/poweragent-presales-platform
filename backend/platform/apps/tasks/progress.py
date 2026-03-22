SECTION_PROGRESS_MAP = {
    "背景介绍": 64,
    "核心挑战识别": 68,
    "建设目标": 72,
    "总体技术架构": 76,
    "技术创新方向": 80,
    "成功案例介绍": 84,
    "技术实施方案": 88,
    "效益分析": 91,
    "效益评估指标": 94,
    "总结": 96,
}


STEP_PROGRESS_MAP = {
    "queued": {"label": "任务排队中", "progress": 2},
    "workflow_started": {"label": "工作流启动中", "progress": 5},
    "intent_identify": {"label": "意图识别中", "progress": 12},
    "intent_identify_completed": {"label": "意图识别完成", "progress": 18},
    "normalize_context": {"label": "场景参数整理中", "progress": 20},
    "normalize_context_completed": {"label": "场景参数整理完成", "progress": 26},
    "retrieve_documents": {"label": "知识检索中", "progress": 34},
    "retrieve_documents_completed": {"label": "知识检索完成", "progress": 42},
    "merge_evidence": {"label": "证据整理中", "progress": 50},
    "merge_evidence_completed": {"label": "证据整理完成", "progress": 56},
    "generate_outline": {"label": "方案大纲生成中", "progress": 60},
    "generate_outline_completed": {"label": "方案大纲生成完成", "progress": 62},
    "expand_sections": {"label": "正文撰写中", "progress": 82},
    "expand_sections_completed": {"label": "正文撰写完成", "progress": 96},
    "generate_case_section": {"label": "正文撰写：成功案例介绍", "progress": 84},
    "generate_case_section_completed": {"label": "成功案例介绍完成", "progress": 86},
    "generate_implementation_section": {"label": "正文撰写：技术实施方案", "progress": 88},
    "generate_implementation_section_completed": {"label": "技术实施方案完成", "progress": 90},
    "generate_kpi_section": {"label": "正文撰写：效益评估指标", "progress": 94},
    "generate_kpi_section_completed": {"label": "效益评估指标完成", "progress": 95},
    "generate_summary_section": {"label": "正文撰写：总结", "progress": 96},
    "generate_summary_section_completed": {"label": "总结完成", "progress": 97},
    "review_solution": {"label": "方案校核中", "progress": 98},
    "review_solution_completed": {"label": "方案校核完成", "progress": 99},
    "finalize_output": {"label": "结果整理完成", "progress": 100},
    "failed": {"label": "执行失败", "progress": 100},
    "completed": {"label": "执行完成", "progress": 100},
    "cancelled": {"label": "任务已取消", "progress": 100},
}


def describe_step(step: str, status: str = "running") -> dict:
    detail = STEP_PROGRESS_MAP.get(step)
    if detail:
        return {"label": detail["label"], "progress": detail["progress"]}
    if step.startswith("generate_section:"):
        section_title = step.split(":", 1)[1]
        return {
            "label": f"正文撰写：{section_title}",
            "progress": SECTION_PROGRESS_MAP.get(section_title, 82),
        }
    if step.startswith("generate_section_completed:"):
        section_title = step.split(":", 1)[1]
        return {
            "label": f"{section_title}完成",
            "progress": min(SECTION_PROGRESS_MAP.get(section_title, 82) + 1, 97),
        }
    if step == "assemble_solution":
        return {"label": "正文拼装中", "progress": 97}
    if step == "assemble_solution_completed":
        return {"label": "正文拼装完成", "progress": 97}
    return {
        "label": "执行完成" if status == "completed" else "处理中",
        "progress": 100 if status == "completed" else 8,
    }
