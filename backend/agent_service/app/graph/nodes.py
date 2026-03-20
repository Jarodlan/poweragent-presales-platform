from app.config import settings
from app.graph.prompts import PROMPTS
from app.graph.state import AgentState
from app.services.llm_gateway import LLMGateway
from app.services.retrieval_service import RetrievalService
from app.services.solution_template import get_solution_template


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


def assemble_solution(state: AgentState) -> AgentState:
    ordered_sections = state.get("section_order", _template_sections())
    content_blocks = []
    for section_title in ordered_sections:
        section_text = state.get("section_contents", {}).get(section_title, "")
        if section_text:
            content_blocks.append(section_text)
    state["final_markdown"] = "# 智能配电网故障诊断解决方案\n\n" + "\n\n".join(content_blocks)
    state["status"] = "assembling_solution"
    return state


def review_solution(state: AgentState) -> AgentState:
    template_section_titles = _template_sections()
    review = _chat_json_or_text(
        [
            {"role": "system", "content": PROMPTS["review_solution"]["system"]},
            {
                "role": "user",
                "content": (
                    f"请检查以下内容：\n{_truncate(state['final_markdown'], 5000)}\n"
                    f"模板必备章节：{template_section_titles}\n"
                    f"{PROMPTS['review_solution']['output_rule']}"
                ),
            },
        ],
        model=settings.qwen_review_model,
        fallback_model=settings.minimax_default_model,
        max_tokens=512,
    )
    state["status"] = "reviewing_solution"
    if review:
        refined_markdown = _chat_json_or_text(
            [
                {"role": "system", "content": PROMPTS["refine_solution"]["system"]},
                {
                    "role": "user",
                    "content": (
                        f"模板必备章节：{template_section_titles}\n"
                        f"修订规则：{PROMPTS['refine_solution']['rules']}\n"
                        f"校核意见：\n{review}\n"
                        f"当前正文：\n{_truncate(state['final_markdown'], 6500)}\n"
                        "请补齐缺失内容、修复截断，并输出修订后的完整Markdown正文。"
                    ),
                },
            ],
            model=settings.qwen_review_model,
            fallback_model=settings.minimax_default_model,
            max_tokens=2400,
        )
        if refined_markdown.startswith("#"):
            state["final_markdown"] = refined_markdown
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
    assumptions = state.get("assumptions", [])
    if review:
        assumptions.append(f"校核结论：{review}")
    state["assumptions"] = assumptions
    return state
