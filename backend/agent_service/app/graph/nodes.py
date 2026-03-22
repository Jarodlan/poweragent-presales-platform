from app.config import settings
from app.graph.prompts import PROMPTS
from app.graph.state import AgentState
from app.services.llm_gateway import LLMGateway
from app.services.retrieval_service import RetrievalService
from app.services.scenario_registry import get_scenario_config, resolve_scenario_id
from app.services.solution_template import get_solution_template, infer_template_key
import re


gateway = LLMGateway()
retrieval_service = RetrievalService()


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


def _active_template(state: AgentState) -> dict[str, object]:
    return get_solution_template(_active_scenario_id(state))


def _active_scenario_id(state: AgentState) -> str:
    if state.get("scenario_id"):
        return str(state["scenario_id"])
    explicit_scenario = str(state.get("params", {}).get("scenario", "") or state.get("params", {}).get("scenario_profile", ""))
    scenario_id = resolve_scenario_id(
        query=state.get("query", ""),
        intent=state.get("normalized_intent", ""),
        explicit=explicit_scenario,
    )
    state["scenario_id"] = scenario_id
    return scenario_id


def _active_scenario_config(state: AgentState) -> dict[str, object]:
    return get_scenario_config(_active_scenario_id(state))


def _derive_dynamic_title(query: str) -> str:
    text = (query or "").strip()
    if not text:
        return "电力行业智能体解决方案"
    prefixes = [
        "请帮我生成一个",
        "帮我生成一个",
        "给我生成一个",
        "请生成一个",
        "生成一个",
        "请帮我做一个",
        "帮我做一个",
        "给我做一个",
        "请输出一个",
        "输出一个",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    for splitter in ["，重点", "重点考虑", "重点关注", "要求", "并说明", "并结合", "，并", "。"]:
        if splitter in text:
            text = text.split(splitter, 1)[0].strip()
    matched = re.match(r"^面向(?P<target>.+?)的(?P<topic>.+?解决方案)$", text)
    if matched:
        target = matched.group("target").strip()
        topic = matched.group("topic").strip()
        text = f"{target}{topic}"
    text = re.sub(r"[。！？!?,，；;：:\s]+$", "", text)
    if "解决方案" not in text:
        text = f"{text}解决方案"
    if len(text) > 40:
        text = text[:40].rstrip("，,。；;：:")
    return text or "电力行业智能体解决方案"


def _resolved_document_title(state: AgentState) -> str:
    scenario_id = _active_scenario_id(state)
    if scenario_id == "other_solution":
        return _derive_dynamic_title(state.get("query", ""))
    solution_template = _active_template(state)
    return str(solution_template.get("document_title", "电力行业解决方案"))


def _template_sections(state: AgentState) -> list[str]:
    solution_template = _active_template(state)
    sections = solution_template.get("section_titles", PROMPTS["generate_outline"]["sections"])
    return [section for section in sections if section not in {"使用原则", "写作约束"}]


def _specialized_sections(state: AgentState) -> list[str]:
    return list(_active_scenario_config(state).get("specialized_sections", []))


def _generic_sections(state: AgentState) -> list[str]:
    specialized = set(_specialized_sections(state))
    return [section for section in _template_sections(state) if section not in specialized]


def _section_requirement(section_title: str) -> str:
    return PROMPTS["expand_sections"].get("section_requirements", {}).get(section_title, "")


def _section_template_block(state: AgentState, section_title: str) -> str:
    solution_template = _active_template(state)
    blocks = solution_template.get("section_blocks", {})
    if not isinstance(blocks, dict):
        return ""
    return str(blocks.get(section_title, ""))


def _scenario_section_guidance(state: AgentState, section_title: str) -> str:
    guidance_map = _active_scenario_config(state).get("section_guidance", {})
    if not isinstance(guidance_map, dict):
        return ""
    return str(guidance_map.get(section_title, ""))


def _shared_cache_prefix(state: AgentState) -> str:
    solution_template = _active_template(state)
    sections = "、".join(_template_sections(state))
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
    if section_title == "成功案例介绍":
        return 1800
    if section_title == "技术实施方案":
        return 2200
    if section_title == "效益评估指标":
        return 700
    if section_title in {"背景介绍", "总体技术架构", "技术创新方向", "效益分析"}:
        return 1200
    return 800


def _normalize_section_heading(section_title: str, content: str) -> str:
    text = (content or "").strip()
    if not text:
        return f"## {section_title}"
    lines = text.splitlines()
    first_non_empty_index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_non_empty_index is None:
        return f"## {section_title}"
    first_line = lines[first_non_empty_index].strip()
    heading_pattern = re.compile(
        rf"^##\s*(?:\d+[.\s、-]+)?(?:第[一二三四五六七八九十\d]+章\s*)?{re.escape(section_title)}\s*$"
    )
    if heading_pattern.match(first_line) or first_line.startswith("## "):
        lines[first_non_empty_index] = f"## {section_title}"
        return "\n".join(lines).strip()
    lines.insert(first_non_empty_index, f"## {section_title}")
    return "\n".join(lines).strip()


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
        if text.count("量化成效") < 2:
            issues.append("成功案例量化成效不足2处")
        if text.count("映射价值") < 2:
            issues.append("成功案例映射价值不足2处")
        if text.endswith(("2周内", "第", "阶段：", "实施过程：")):
            issues.append("成功案例章节疑似在案例二中途截断")
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
    ordered_sections = state.get("section_order", _template_sections(state))
    content_blocks = []
    for section_title in ordered_sections:
        section_text = state.get("section_contents", {}).get(section_title, "")
        if section_text:
            content_blocks.append(section_text.strip())
    document_title = _resolved_document_title(state)
    return f"# {document_title}\n\n" + "\n\n".join(content_blocks)


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
    if not content:
        query = state["query"]
        content = infer_template_key(query=query, intent="")
    state["normalized_intent"] = content or infer_template_key(query=user_query, intent="")
    state["scenario_id"] = resolve_scenario_id(
        query=user_query,
        intent=state["normalized_intent"],
        explicit=str(state.get("params", {}).get("scenario", "") or state.get("params", {}).get("scenario_profile", "")),
    )
    state["status"] = "intent_identifying"
    state.setdefault("metadata", {})
    state["metadata"] = {
        "prompt": PROMPTS["intent_identify"],
        "scenario_config": _active_scenario_config(state),
    }
    return state


def normalize_context(state: AgentState) -> AgentState:
    params = state.get("params", {})
    defaults = dict(_active_scenario_config(state).get("default_context", {}))
    normalized_context = {}
    for key, value in defaults.items():
        normalized_context[key] = params.get(key, value)
    state["normalized_context"] = normalized_context
    state["status"] = "context_normalizing"
    return state


def retrieve_documents(state: AgentState) -> AgentState:
    if state.get("params", {}).get("skip_ragflow"):
        state["documents"] = []
        state["status"] = "retrieving_documents"
        return state
    retrieval_query = state["query"]
    normalized_intent = state.get("normalized_intent", "").strip()
    if normalized_intent and normalized_intent not in retrieval_query:
        retrieval_query = f"{retrieval_query}\n场景标签：{normalized_intent}"
    state["documents"] = retrieval_service.search(
        query=retrieval_query,
        filters=state.get("normalized_context", {}),
        scenario_id=_active_scenario_id(state),
    )
    state["status"] = "retrieving_documents"
    return state


def merge_evidence(state: AgentState) -> AgentState:
    docs = state.get("documents", [])
    external_evidence = state.get("params", {}).get("external_evidence", "")
    docs_text = "\n".join(
        f"[{item['source_type']}] {item.get('title', '')}\n{item.get('snippet', '')[:220]}"
        for item in docs[:6]
    )
    if external_evidence:
        docs_text = f"{docs_text}\n[external_public_sources]\n{external_evidence}".strip()
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
    solution_template = _active_template(state)
    evidence_excerpt = _truncate(state.get("evidence", {}).get("merged_text", ""), 1800)
    template_section_titles = _template_sections(state)
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
    section_block = _truncate(_section_template_block(state, section_title), 1500)
    section_requirement = _section_requirement(section_title)
    scenario_guidance = _scenario_section_guidance(state, section_title)
    previous_sections = _truncate(state.get("generated_sections_context", ""), 1600)
    shared_prefix = _shared_cache_prefix(state)
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
                    f"场景专项要求：{scenario_guidance or '无'}\n"
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
    section_content = _normalize_section_heading(section_title, section_content)
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
    section_block = _truncate(_section_template_block(state, section_title), 1800)
    scenario_guidance = _scenario_section_guidance(state, section_title)
    shared_prefix = _shared_cache_prefix(state)
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
                    f"场景专项要求：{scenario_guidance or '无'}\n"
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
    content = _normalize_section_heading(section_title, content)
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


def generate_case_section(state: AgentState) -> AgentState:
    return _generate_special_section(
        state,
        section_title="成功案例介绍",
        prompt_key="generate_case_section",
        max_tokens=2000,
    )


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
    section_titles = state.get("section_order", _template_sections(state))
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
                        f"章节要求：{_section_requirement(section_title) or _section_template_block(state, section_title)}\n"
                        f"场景专项要求：{_scenario_section_guidance(state, section_title) or '无'}\n"
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
        elif section_title == "成功案例介绍":
            state = _generate_special_section(
                state,
                section_title=section_title,
                prompt_key="generate_case_section",
                max_tokens=2000,
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
            repaired = _normalize_section_heading(section_title, repaired)
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
