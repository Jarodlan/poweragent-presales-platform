from .nodes import expand_sections, generate_outline, intent_identify, normalize_context, review_solution
from .state import AgentState


def run_workflow(state: AgentState) -> AgentState:
    """
    Sequential MVP skeleton.
    TODO:
    - Replace with LangGraph graph composition
    - Insert retrieval and LLM-backed nodes
    """
    state = intent_identify(state)
    state = normalize_context(state)
    state = generate_outline(state)
    state = expand_sections(state)
    state = review_solution(state)
    state["status"] = "completed"
    return state
