import uuid
from typing import Any

import httpx
from app.graph.workflow import run_workflow


RUN_STORE: dict[str, dict] = {}


def create_run(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    RUN_STORE[run_id] = {
        "run_id": run_id,
        "status": "running",
        "step": "workflow_started",
        "request": payload,
        "result": None,
    }
    return RUN_STORE[run_id]


def execute_run(run_id: str) -> dict[str, Any]:
    payload = RUN_STORE[run_id]["request"]
    state = {
        "task_id": payload["task_id"],
        "conversation_id": payload["conversation_id"],
        "assistant_message_id": payload["assistant_message_id"],
        "query": payload["query"],
        "params": payload.get("params", {}),
        "status": "running",
        "errors": [],
    }
    try:
        def update_progress(step: str, current_state: dict[str, Any]) -> None:
            RUN_STORE[run_id]["step"] = step
            RUN_STORE[run_id]["status"] = current_state.get("status", "running")

        result = run_workflow(state, progress_callback=update_progress)
        RUN_STORE[run_id]["status"] = result.get("status", "completed")
        RUN_STORE[run_id]["step"] = "finalize_output"
        RUN_STORE[run_id]["result"] = result
        post_callback(
            payload["callback_url"],
            {
                "run_id": run_id,
                "status": RUN_STORE[run_id]["status"],
                "current_step": RUN_STORE[run_id]["step"],
                "result": {
                    "summary": result.get("summary", ""),
                    "final_markdown": result.get("final_markdown", ""),
                    "evidence_cards": result.get("evidence_cards", []),
                    "assumptions": result.get("assumptions", []),
                    "normalized_intent": result.get("normalized_intent", ""),
                    "normalized_context": result.get("normalized_context", {}),
                },
            },
        )
    except Exception as exc:
        RUN_STORE[run_id]["status"] = "failed"
        RUN_STORE[run_id]["step"] = "failed"
        RUN_STORE[run_id]["result"] = None
        post_callback(
            payload["callback_url"],
            {
                "run_id": run_id,
                "status": "failed",
                "current_step": "failed",
                "error_code": "AGENT_RUN_FAILED",
                "error_message": str(exc),
            },
        )
    return RUN_STORE[run_id]


def get_run(run_id: str) -> dict:
    return RUN_STORE[run_id]


def post_callback(callback_url: str, payload: dict[str, Any]) -> None:
    with httpx.Client(timeout=15) as client:
        client.post(callback_url, json=payload)
