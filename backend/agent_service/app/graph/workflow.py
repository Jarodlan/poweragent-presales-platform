from collections.abc import Callable

from .nodes import (
    expand_sections,
    generate_outline,
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
        ("expand_sections", expand_sections),
        ("review_solution", review_solution),
    ]
    for step_name, step_func in steps:
        if progress_callback:
            progress_callback(step_name, state)
        state = step_func(state)
        if progress_callback:
            progress_callback(f"{step_name}_completed", state)
    state["status"] = "completed"
    return state
