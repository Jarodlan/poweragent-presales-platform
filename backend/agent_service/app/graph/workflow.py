from collections.abc import Callable

from .nodes import (
    assemble_solution,
    generate_outline,
    generate_section,
    intent_identify,
    merge_evidence,
    normalize_context,
    retrieve_documents,
    review_solution,
)
from .state import AgentState


ProgressCallback = Callable[[str, AgentState], None]


def run_workflow(
    state: AgentState,
    *,
    progress_callback: ProgressCallback | None = None,
) -> AgentState:
    """
    Sequential MVP workflow.
    """
    steps = [
        ("intent_identify", intent_identify),
        ("normalize_context", normalize_context),
        ("retrieve_documents", retrieve_documents),
        ("merge_evidence", merge_evidence),
        ("generate_outline", generate_outline),
    ]
    for step_name, step_func in steps:
        if progress_callback:
            progress_callback(step_name, state)
        state = step_func(state)
        if progress_callback:
            progress_callback(f"{step_name}_completed", state)
    for section_title in state.get("section_order", []):
        step_name = f"generate_section:{section_title}"
        if progress_callback:
            progress_callback(step_name, state)
        state = generate_section(state, section_title)
        if progress_callback:
            progress_callback(f"generate_section_completed:{section_title}", state)
    if progress_callback:
        progress_callback("assemble_solution", state)
    state = assemble_solution(state)
    if progress_callback:
        progress_callback("assemble_solution_completed", state)
    if progress_callback:
        progress_callback("review_solution", state)
    state = review_solution(state)
    if progress_callback:
        progress_callback("review_solution_completed", state)
    state["status"] = "completed"
    return state
