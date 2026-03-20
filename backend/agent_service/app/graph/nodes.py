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
    template_section_titles = solution_template.get("section_titles", PROMPTS["generate_outline"]["sections"])
    template_excerpt = _truncate(str(solution_template.get("template_excerpt", "")), 2200)
    prompt = (
        f"{PROMPTS['generate_outline']['system']}\n"
        f"参考固定章节：{template_section_titles}\n"
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
    return state


def expand_sections(state: AgentState) -> AgentState:
    evidence_excerpt = _truncate(state.get("evidence", {}).get("merged_text", ""), 1800)
    outline_excerpt = _truncate(state.get("outline", ""), 1200)
    template_excerpt = _truncate(str(solution_template.get("template_excerpt", "")), 3000)
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
    final_markdown = _chat_json_or_text(
        [
            {"role": "system", "content": PROMPTS["expand_sections"]["system"]},
            {
                "role": "user",
                "content": (
                    f"用户需求：{state['query']}\n"
                    f"标准化场景：{state.get('normalized_intent', '')}\n"
                    f"上下文：{state.get('normalized_context', {})}\n"
                    f"检索证据：{evidence_excerpt}\n"
                    f"方案大纲：\n{outline_excerpt}\n"
                    f"必须遵循的解决方案模板：\n{template_excerpt}\n"
                    f"规则：{PROMPTS['expand_sections']['rules']}\n"
                    "请输出完整 Markdown 方案正文。"
                ),
            },
        ],
        model=settings.qwen_default_model,
        fallback_model=settings.minimax_default_model,
        max_tokens=1800,
    )
    state["summary"] = summary or f"本方案围绕“{state['query']}”生成。"
    state["final_markdown"] = final_markdown or (
        "# 电力行业解决方案生成 Agent MVP\n\n"
        "当前模型已接通，但正文生成未返回内容，请检查 API Key 或模型配置。\n"
    )
    state["status"] = "expanding_sections"
    return state


def review_solution(state: AgentState) -> AgentState:
    template_section_titles = solution_template.get("section_titles", [])
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
