from app.graph.prompts import PROMPTS
from app.graph.state import AgentState


def intent_identify(state: AgentState) -> AgentState:
    state["normalized_intent"] = "fault_diagnosis_solution"
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


def generate_outline(state: AgentState) -> AgentState:
    sections = PROMPTS["generate_outline"]["sections"]
    state["outline"] = "\n".join(f"{idx + 1}. {title}" for idx, title in enumerate(sections))
    state["status"] = "generating_outline"
    return state


def expand_sections(state: AgentState) -> AgentState:
    state["summary"] = f"本方案围绕“{state['query']}”生成，当前为 MVP 骨架版本。"
    state["final_markdown"] = (
        "# 电力行业解决方案生成 Agent MVP\n\n"
        "## 建设目标\n\n"
        "构建面向电力行业的方案生成助手。\n\n"
        "## 当前骨架状态\n\n"
        "已接入 Django 平台层、Agent Service、LangGraph 节点骨架与 Prompt 模板。\n\n"
        f"## 方案大纲\n\n{state['outline']}\n"
    )
    state["status"] = "expanding_sections"
    return state


def review_solution(state: AgentState) -> AgentState:
    state["status"] = "reviewing_solution"
    state["evidence_cards"] = []
    return state
