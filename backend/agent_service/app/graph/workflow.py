from .state import AgentState


def run_workflow(state: AgentState) -> AgentState:
    """
    Skeleton workflow implementation.
    TODO:
    - Replace with LangGraph graph composition
    - Add retrieval, outline generation, section expansion, and review nodes
    """
    query = state["query"]
    state["normalized_intent"] = "fault_diagnosis_solution"
    state["normalized_context"] = {
        "grid_environment": state.get("params", {}).get("grid_environment", "distribution_network"),
        "equipment_type": state.get("params", {}).get("equipment_type", "comprehensive"),
    }
    state["summary"] = f"本方案基于需求“{query}”生成，当前为 Agent Service 骨架版本。"
    state["final_markdown"] = (
        "# 电力行业解决方案生成 Agent\n\n"
        "## 当前状态\n\n"
        "后端骨架已生成，待接入 LangGraph 工作流、RAGFlow 检索和 Qwen/MiniMax 模型。\n"
    )
    state["evidence_cards"] = []
    state["status"] = "completed"
    return state
