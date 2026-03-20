from app.config import settings
from app.graph.prompts import PROMPTS
from app.graph.state import AgentState
from app.services.llm_gateway import LLMGateway
from app.services.retrieval_service import RetrievalService
from app.services.solution_template import get_solution_template
import re


gateway = LLMGateway()
retrieval_service = RetrievalService()
solution_template = get_solution_template()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...[truncated]"


def _chat_json_or_text(
    messages: list[dict],
    *,
    model: str,
    fallback_model: str,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> str:
    response = gateway.chat_with_fallback(
        {
            "provider": "qwen",
            "model": model,
            "fallback_model": fallback_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    )
    return response.get("content", "").strip()


def _template_sections() -> list[str]:
    sections = solution_template.get("section_titles", PROMPTS["generate_outline"]["sections"])
    return [section for section in sections if section not in {"使用原则", "写作约束"}]


def _specialized_sections() -> list[str]:
    return ["技术实施方案", "效益评估指标", "总结"]


def _generic_sections() -> list[str]:
    return [section for section in _template_sections() if section not in _specialized_sections()]


def _section_requirement(section_title: str) -> str:
    return PROMPTS["expand_sections"].get("section_requirements", {}).get(section_title, "")


def _section_template_block(section_title: str) -> str:
    blocks = solution_template.get("section_blocks", {})
    if not isinstance(blocks, dict):
        return ""
    return str(blocks.get(section_title, ""))


def _shared_cache_prefix() -> str:
    sections = "、".join(_template_sections())
    template_excerpt = _truncate(str(solution_template.get("template_excerpt", "")), 2600)
    reference_excerpt = _truncate(str(solution_template.get("reference_excerpt", "")), 2600)
    return (
        "你正在为电力行业解决方案生成Agent生成正式方案正文。\n"
        f"必须遵循的正文章节顺序：{sections}\n"
        "正文不能输出证据卡、校核意见、使用原则、写作约束等附属内容。\n"
        "请优先保证“技术实施方案”“效益评估指标”“总结”三章完整输出。\n"
        "以下为模板摘录：\n"
        f"{template_excerpt}\n\n"
        "以下为参考方案摘录：\n"
        f"{reference_excerpt}\n"
    )


def _section_max_tokens(section_title: str) -> int:
    if section_title == "技术实施方案":
        return 1800
    if section_title == "效益评估指标":
        return 700
    if section_title in {"背景介绍", "总体技术架构", "技术创新方向"}:
        return 1000
    return 800


def _programmatic_section_issues(section_title: str, content: str) -> list[str]:
    issues: list[str] = []
    text = (content or "").strip()
    if not text:
        return ["章节为空"]
    if not text.startswith(f"## {section_title}"):
        issues.append("未以正确的二级标题开头")
    if text.endswith(("：", ":", "-", "（", "(")):
        issues.append("章节结尾疑似截断")
    if section_title == "技术创新方向":
        item_count = len(
            re.findall(
                r"(?m)^\s*(?:\*\*)?(?:\d+\.)|^\s*(?:\*\*)?[一二三四五六七八九十]+、",
                text,
            )
        )
        if item_count < 3:
            issues.append("技术创新方向不足3项")
    if section_title == "成功案例介绍":
        case_count = len(re.findall(r"案例[一二三四五六七八九十\d]", text))
        if case_count < 2:
            issues.append("成功案例数量不足2个")
    if section_title == "技术实施方案":
        step_count = len(
            re.findall(r"(?m)^\s*###\s*步骤(?:[一二三四五六七八九十]|\d+)", text)
        )
        if step_count < 5:
            issues.append("技术实施方案未完整覆盖5个步骤")
    if section_title == "效益分析" and len(text) < 220:
        issues.append("效益分析内容偏短")
    if section_title == "效益评估指标":
        if "KPI名称 | 目标值 | 测量方式" not in text:
            issues.append("缺少KPI表头")
        table_rows = sum(1 for line in text.splitlines() if "|" in line)
        if table_rows < 7:
            issues.append("KPI表格行数不足")
    if section_title == "总结" and len(text) < 140:
        issues.append("总结内容偏短")
    return issues


def _assemble_markdown_from_sections(state: AgentState) -> str:
    ordered_sections = state.get("section_order", _template_sections())
    content_blocks = []
    for section_title in ordered_sections:
        section_text = state.get("section_contents", {}).get(section_title, "")
        if section_text:
            content_blocks.append(section_text.strip())
    return "# 智能配电网故障诊断解决方案\n\n" + "\n\n".join(content_blocks)


def intent_identify(state: AgentState) -> AgentState:
    user_query = state["query"]
    content = _chat_json_or_text(
        [
            {"role": "system", "content": PROMPTS["intent_identify"]["system"]},
            {
                "role": "user",
                "content": f"{PROMPTS['intent_identify']['output_rule']}\n用户问题：{user_query}",
            },
        ],
        model=settings.qwen_default_model,
        fallback_model=settings.minimax_fast_model,
        max_tokens=64,
    )
    state["normalized_intent"] = content or "fault_diagnosis_solution"
    state["status"] = "intent_identifying"
    state.setdefault("metadata", {})
    state["metadata"] = {"prompt": PROMPTS["intent_identify"]}
    return state


def normalize_context(state: AgentState) -> AgentState:
    params = state.get("params", {})
    state["normalized_context"] = {
        "grid_environment": params.get("grid_environment", "distribution_network"),
        "equipment_type": params.get("equipment_type", "comprehensive"),
        "data_basis": params.get(
            "data_basis",
            ["scada", "online_monitoring", "historical_workorder"],
        ),
        "target_capability": params.get(
            "target_capability",
            ["fault_diagnosis", "root_cause_analysis"],
        ),
    }
    state["status"] = "context_normalizing"
    return state


def retrieve_documents(state: AgentState) -> AgentState:
    retrieval_query = state["query"]
    normalized_intent = state.get("normalized_intent", "").strip()
    if normalized_intent and normalized_intent not in retrieval_query:
        retrieval_query = f"{retrieval_query}\n场景标签：{normalized_intent}"
    state["documents"] = retrieval_service.search(
        query=retrieval_query,
        filters=state.get("normalized_context", {}),
    )
    state["status"] = "retrieving_documents"
    return state


def merge_evidence(state: AgentState) -> AgentState:
    docs = state.get("documents", [])
    docs_text = "\n".join(
        f"[{item['source_type']}] {item.get('title', '')}\n{item.get('snippet', '')[:220]}"
        for item in docs[:6]
    )
    content = _chat_json_or_text(
        [
            {"role": "system", "content": PROMPTS["merge_evidence"]["system"]},
            {
                "role": "user",
                "content": (
                    f"当前场景：{state.get('normalized_intent', '')}\n"
                    f"检索结果：\n{docs_text}\n"
                    f"{PROMPTS['merge_evidence']['output_rule']}"
                ),
            },
        ],
        model=settings.qwen_default_model,
        fallback_model=settings.minimax_fast_model,
        max_tokens=900,
    )
    state["evidence"] = {
        "merged_text": _truncate(content, 2200),
        "documents": docs[:6],
    }
    state["status"] = "merging_evidence"
    return state


def generate_outline(state: AgentState) -> AgentState:
    evidence_excerpt = _truncate(state.get("evidence", {}).get("merged_text", ""), 1800)
    template_section_titles = _template_sections()
    template_excerpt = _truncate(str(solution_template.get("template_excerpt", "")), 2200)
    prompt = (
        f"{PROMPTS['generate_outline']['system']}\n"
        f"参考固定章节：{template_section_titles}\n"
        f"大纲规则：{PROMPTS['generate_outline']['rules']}\n"
        f"用户需求：{state['query']}\n"
        f"标准化场景：{state.get('normalized_intent', '')}\n"
        f"上下文：{state.get('normalized_context', {})}\n"
        f"检索证据：{evidence_excerpt}\n"
        f"解决方案模板摘录：\n{template_excerpt}\n"
        "请严格遵循模板的章节顺序与专业风格输出有编号的大纲。"
    )
    content = _chat_json_or_text(
        [
            {"role": "system", "content": PROMPTS["generate_outline"]["system"]},
            {"role": "user", "content": prompt},
        ],
        model=settings.qwen_review_model,
        fallback_model=settings.minimax_default_model,
        max_tokens=1200,
    )
    state["outline"] = content or "\n".join(
        f"{idx + 1}. {title}" for idx, title in enumerate(template_section_titles)
    )
    state["status"] = "generating_outline"
    state["section_order"] = template_section_titles
    return state


def generate_section_content(
    state: AgentState,
    *,
    section_title: str,
    review_feedback: str = "",
) -> str:
    outline_excerpt = _truncate(state.get("outline", ""), 1600)
    evidence_excerpt = _truncate(state.get("evidence", {}).get("merged_text", ""), 2000)
    section_block = _truncate(_section_template_block(section_title), 1500)
    section_requirement = _section_requirement(section_title)
    previous_sections = _truncate(state.get("generated_sections_context", ""), 1600)
    shared_prefix = _shared_cache_prefix()
    content = _chat_json_or_text(
        [
            {
                "role": "system",
                "content": (
                    f"{PROMPTS['expand_sections']['system']}\n"
                    f"{shared_prefix}\n"
                    f"通用规则：{PROMPTS['expand_sections']['rules']}\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"当前章节：{section_title}\n"
                    f"章节写作要求：{section_requirement}\n"
                    f"用户需求：{state['query']}\n"
                    f"标准化场景：{state.get('normalized_intent', '')}\n"
                    f"上下文：{state.get('normalized_context', {})}\n"
                    f"方案大纲：\n{outline_excerpt}\n"
                    f"检索证据：\n{evidence_excerpt}\n"
                    f"模板中的本章节要求：\n{section_block}\n"
                    f"已完成章节摘要：\n{previous_sections}\n"
                    f"章节修订意见：\n{review_feedback or '无'}\n"
                    "请只输出当前章节的 Markdown 内容，必须以二级标题开头，且写完整。"
                ),
            },
        ],
        model=settings.qwen_default_model,
        fallback_model=settings.minimax_default_model,
        max_tokens=_section_max_tokens(section_title),
    )
    return content.strip()


def generate_section(state: AgentState, section_title: str) -> AgentState:
    section_contents = state.get("section_contents", {})
    state["current_section_title"] = section_title
    if not state.get("summary"):
        summary = _chat_json_or_text(
            [
                {"role": "system", "content": "你是电力行业方案摘要生成助手。请输出 4 到 6 句项目化摘要。"},
                {
                    "role": "user",
                    "content": f"用户需求：{state['query']}\n场景：{state.get('normalized_intent', '')}\n上下文：{state.get('normalized_context', {})}",
                },
            ],
            model=settings.qwen_default_model,
            fallback_model=settings.minimax_fast_model,
            max_tokens=300,
        )
        state["summary"] = summary or f"本方案围绕“{state['query']}”生成。"
    section_content = generate_section_content(state, section_title=section_title)
    if not section_content.startswith("## "):
        section_content = f"## {section_title}\n\n{section_content}"
    section_contents[section_title] = section_content
    state["section_contents"] = section_contents
    existing_context = state.get("generated_sections_context", "")
    state["generated_sections_context"] = (
        existing_context
        + f"{section_title}: "
        + f"{_truncate(section_content.replace('\\n', ' '), 240)}\n"
    )
    state["status"] = "expanding_sections"
    return state


def _generate_special_section(
    state: AgentState,
    *,
    section_title: str,
    prompt_key: str,
    max_tokens: int,
    review_feedback: str = "",
) -> AgentState:
    section_contents = state.get("section_contents", {})
    evidence_excerpt = _truncate(state.get("evidence", {}).get("merged_text", ""), 2200)
    outline_excerpt = _truncate(state.get("outline", ""), 1800)
    previous_sections = _truncate(state.get("generated_sections_context", ""), 2200)
    section_block = _truncate(_section_template_block(section_title), 1800)
    shared_prefix = _shared_cache_prefix()
    prompt = PROMPTS[prompt_key]
    content = _chat_json_or_text(
        [
            {
                "role": "system",
                "content": (
                    f"{prompt['system']}\n"
                    f"{shared_prefix}\n"
                    f"规则：{prompt['rules']}\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户需求：{state['query']}\n"
                    f"标准化场景：{state.get('normalized_intent', '')}\n"
                    f"上下文：{state.get('normalized_context', {})}\n"
                    f"方案大纲：\n{outline_excerpt}\n"
                    f"检索证据：\n{evidence_excerpt}\n"
                    f"模板中的本章节要求：\n{section_block}\n"
                    f"已完成章节摘要：\n{previous_sections}\n"
                    f"章节修订意见：\n{review_feedback or '无'}\n"
                    f"请只输出章节“{section_title}”的Markdown正文。"
                ),
            },
        ],
        model=settings.qwen_review_model,
        fallback_model=settings.minimax_default_model,
        max_tokens=max_tokens,
    )
    if not content.startswith("## "):
        content = f"## {section_title}\n\n{content}"
    section_contents[section_title] = content.strip()
    state["section_contents"] = section_contents
    existing_context = state.get("generated_sections_context", "")
    state["generated_sections_context"] = (
        existing_context
        + f"{section_title}: "
        + f"{_truncate(content.replace('\\n', ' '), 260)}\n"
    )
    state["status"] = "expanding_sections"
    return state


def generate_implementation_section(state: AgentState) -> AgentState:
    return _generate_special_section(
        state,
        section_title="技术实施方案",
        prompt_key="generate_implementation_section",
        max_tokens=2200,
    )


def generate_kpi_section(state: AgentState) -> AgentState:
    return _generate_special_section(
        state,
        section_title="效益评估指标",
        prompt_key="generate_kpi_section",
        max_tokens=1200,
    )


def generate_summary_section(state: AgentState) -> AgentState:
    return _generate_special_section(
        state,
        section_title="总结",
        prompt_key="generate_summary_section",
        max_tokens=900,
    )


def assemble_solution(state: AgentState) -> AgentState:
    state["final_markdown"] = _assemble_markdown_from_sections(state)
    state["status"] = "assembling_solution"
    return state


def review_solution(state: AgentState) -> AgentState:
    state["status"] = "reviewing_solution"
    section_titles = state.get("section_order", _template_sections())
    review_notes: list[str] = []
    for section_title in section_titles:
        content = state.get("section_contents", {}).get(section_title, "")
        programmatic_issues = _programmatic_section_issues(section_title, content)
        llm_review = _chat_json_or_text(
            [
                {"role": "system", "content": PROMPTS["review_section"]["system"]},
                {
                    "role": "user",
                    "content": (
                        f"章节标题：{section_title}\n"
                        f"章节要求：{_section_requirement(section_title) or _section_template_block(section_title)}\n"
                        f"当前章节内容：\n{_truncate(content, 3200)}\n"
                        f"程序规则发现的问题：{programmatic_issues or ['无']}\n"
                        f"{PROMPTS['review_section']['output_rule']}"
                    ),
                },
            ],
            model=settings.qwen_review_model,
            fallback_model=settings.minimax_fast_model,
            max_tokens=220,
        ).strip()
        if llm_review.upper().startswith("PASS") and not programmatic_issues:
            continue
        repair_feedback = "；".join(programmatic_issues) if programmatic_issues else ""
        if llm_review and not llm_review.upper().startswith("PASS"):
            repair_feedback = f"{repair_feedback}；{llm_review}".strip("；")
        review_notes.append(f"{section_title}: {repair_feedback or '章节已校核'}")
        if section_title == "技术实施方案":
            state = _generate_special_section(
                state,
                section_title=section_title,
                prompt_key="generate_implementation_section",
                max_tokens=2200,
                review_feedback=repair_feedback,
            )
        elif section_title == "效益评估指标":
            state = _generate_special_section(
                state,
                section_title=section_title,
                prompt_key="generate_kpi_section",
                max_tokens=1200,
                review_feedback=repair_feedback,
            )
        elif section_title == "总结":
            state = _generate_special_section(
                state,
                section_title=section_title,
                prompt_key="generate_summary_section",
                max_tokens=900,
                review_feedback=repair_feedback,
            )
        else:
            repaired = generate_section_content(
                state,
                section_title=section_title,
                review_feedback=repair_feedback,
            )
            if not repaired.startswith("## "):
                repaired = f"## {section_title}\n\n{repaired}"
            state.setdefault("section_contents", {})
            state["section_contents"][section_title] = repaired.strip()
    state["assumptions"] = review_notes
    state["final_markdown"] = _assemble_markdown_from_sections(state)
    docs = state.get("documents", [])
    state["evidence_cards"] = [
        {
            "source_type": item.get("source_type", ""),
            "title": item.get("title", ""),
            "summary": item.get("snippet", "")[:180],
            "used_in_section": "方案生成",
            "metadata": item.get("metadata", {}),
        }
        for item in docs[:6]
    ]
    return state
