from collections.abc import Callable

from .nodes import (
    assemble_solution,
    generate_case_section,
    generate_implementation_section,
    generate_kpi_section,
    generate_outline,
    generate_section,
    generate_summary_section,
    intent_identify,
    merge_evidence,
    normalize_context,
    retrieve_documents,
    review_solution,
)
from .state import AgentState
from app.services.scenario_registry import get_scenario_config, resolve_scenario_id


ProgressCallback = Callable[[str, AgentState], None]


SPECIALIZED_STEP_MAP = {
    "成功案例介绍": ("generate_case_section", generate_case_section),
    "技术实施方案": ("generate_implementation_section", generate_implementation_section),
    "效益评估指标": ("generate_kpi_section", generate_kpi_section),
    "总结": ("generate_summary_section", generate_summary_section),
}


def run_workflow(
    state: AgentState,
    *,
    progress_callback: ProgressCallback | None = None,
) -> AgentState:
    """
    Sequential MVP workflow.
    """
    scenario_id = state.get("scenario_id") or resolve_scenario_id(
        query=state.get("query", ""),
        intent=state.get("normalized_intent", ""),
        explicit=str(state.get("params", {}).get("scenario_profile", "")),
    )
    state["scenario_id"] = scenario_id
    scenario_config = get_scenario_config(scenario_id)

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
    specialized_sections = set(scenario_config.get("specialized_sections", []))
    for section_title in [title for title in state.get("section_order", []) if title not in specialized_sections]:
        step_name = f"generate_section:{section_title}"
        if progress_callback:
            progress_callback(step_name, state)
        state = generate_section(state, section_title)
        if progress_callback:
            progress_callback(f"generate_section_completed:{section_title}", state)
    specialized_steps = [
        SPECIALIZED_STEP_MAP[section_title]
        for section_title in state.get("section_order", [])
        if section_title in SPECIALIZED_STEP_MAP and section_title in specialized_sections
    ]
    for step_name, step_func in specialized_steps:
        if progress_callback:
            progress_callback(step_name, state)
        state = step_func(state)
        if progress_callback:
            progress_callback(f"{step_name}_completed", state)
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
