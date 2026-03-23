import asyncio
import base64
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect

from app.schemas.run import AgentRunCreateRequest, AgentRunResponse, AgentRunStatusResponse
from app.services.agent_runner import create_run, execute_run, get_run
from app.services.progress import describe_step
from app.services.realtime_asr import QwenRealtimeAsrBridge, parse_ws_message


router = APIRouter()
logger = logging.getLogger(__name__)


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
    progress_meta = describe_step(run["step"], run["status"])
    return AgentRunStatusResponse(
        run_id=run["run_id"],
        status=run["status"],
        step=run["step"],
        step_label=progress_meta["label"],
        progress=progress_meta["progress"],
        result=run["result"],
    )


@router.websocket("/ws/customer-demand/asr")
async def customer_demand_realtime_asr(websocket: WebSocket) -> None:
    await websocket.accept()
    bridge: QwenRealtimeAsrBridge | None = None
    forward_task: asyncio.Task[None] | None = None

    async def forward_events() -> None:
        assert bridge is not None
        while True:
            event = await bridge.event_queue.get()
            await websocket.send_json(event)

    try:
        init_payload = parse_ws_message(await websocket.receive_text())
        if init_payload.get("type") != "session.start":
            await websocket.send_json({"type": "error", "message": "首条消息必须是 session.start"})
            await websocket.close(code=1003)
            return

        bridge = QwenRealtimeAsrBridge(
            language=str(init_payload.get("language") or "zh"),
            sample_rate=int(init_payload.get("sample_rate") or 16000),
            corpus_text=str(init_payload.get("corpus_text") or ""),
        )
        await bridge.connect()
        forward_task = asyncio.create_task(forward_events())
        await websocket.send_json(
            {
                "type": "session.ready",
                "model": "qwen3-asr-flash-realtime",
                "sample_rate": bridge.sample_rate,
            }
        )

        while True:
            payload = parse_ws_message(await websocket.receive_text())
            message_type = payload.get("type")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message_type == "audio_chunk":
                audio_b64 = str(payload.get("audio_b64") or "")
                mime_type = str(payload.get("mime_type") or "audio/webm")
                if not audio_b64:
                    continue
                audio_bytes = base64.b64decode(audio_b64)
                logger.info("customer_demand_asr audio_chunk received mime=%s bytes=%s", mime_type, len(audio_bytes))
                await bridge.append_media_chunk(audio_bytes, mime_type)
                continue
            if message_type == "session.stop":
                await bridge.finish()
                await asyncio.sleep(0.5)
                await websocket.send_json({"type": "session.ended"})
                break

        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover - runtime safety for websocket sessions
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if forward_task:
            forward_task.cancel()
        if bridge is not None:
            try:
                await bridge.close()
            except Exception:
                pass
