import uuid

from app.graph.workflow import run_workflow


RUN_STORE: dict[str, dict] = {}


def create_run(payload: dict) -> dict:
    run_id = str(uuid.uuid4())
    RUN_STORE[run_id] = {
        "run_id": run_id,
        "status": "running",
        "step": "workflow_started",
        "request": payload,
        "result": None,
    }

    state = {
        "task_id": payload["task_id"],
        "conversation_id": payload["conversation_id"],
        "assistant_message_id": payload["assistant_message_id"],
        "query": payload["query"],
        "params": payload.get("params", {}),
        "status": "running",
        "errors": [],
    }
    result = run_workflow(state)
    RUN_STORE[run_id]["status"] = result.get("status", "completed")
    RUN_STORE[run_id]["step"] = "finalize_output"
    RUN_STORE[run_id]["result"] = result
    return RUN_STORE[run_id]


def get_run(run_id: str) -> dict:
    return RUN_STORE[run_id]
