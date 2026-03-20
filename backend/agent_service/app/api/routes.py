from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.run import AgentRunCreateRequest, AgentRunResponse, AgentRunStatusResponse
from app.services.agent_runner import create_run, execute_run, get_run


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/internal/agent/runs", response_model=AgentRunResponse)
def start_run(payload: AgentRunCreateRequest, background_tasks: BackgroundTasks) -> AgentRunResponse:
    run = create_run(payload.model_dump())
    background_tasks.add_task(execute_run, run["run_id"])
    return AgentRunResponse(run_id=run["run_id"], status=run["status"])


@router.get("/internal/agent/runs/{run_id}", response_model=AgentRunStatusResponse)
def get_run_status(run_id: str) -> AgentRunStatusResponse:
    try:
        run = get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return AgentRunStatusResponse(
        run_id=run["run_id"],
        status=run["status"],
        step=run["step"],
        result=run["result"],
    )
