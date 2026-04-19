"""
FastAPI server for the Rail Track Digital Twin.

Configuration via environment variables:
    TRACK_CONFIG        Comma-separated health states, e.g. "0,1,2,1,0" (default)
    SIMULATOR_TYPE      "csv" or "synthetic" (default: csv)
    TICK_INTERVAL_S     Seconds between OODA ticks (default: 1.0)
    WORK_ORDER_API_URL  Base URL of external work order system (optional)
    WORK_ORDER_API_KEY  Bearer token for work order API (optional)

Endpoints:
    GET  /health        Liveness check
    GET  /state         Latest TwinState snapshot (JSON)
    POST /correction    Apply human-in-the-loop segment correction
    POST /reset         Reset all Bayesian trackers to uniform priors
    WS   /ws            WebSocket stream — pushes TwinStateResponse each tick
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from api.models import TwinStateResponse, CorrectionRequest, TrackConfigRequest, twin_state_to_response
from api.websocket import WebSocketManager
from digital_twin_v2.orchestrator import DigitalTwin
from integrations.work_orders import WorkOrderClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _track_config() -> list[int]:
    raw = os.getenv("TRACK_CONFIG", "0,1,2,1,0")
    return [int(x.strip()) for x in raw.split(",")]


def _tick_interval() -> float:
    return float(os.getenv("TICK_INTERVAL_S", "1.0"))


def _build_simulator():
    sim_type = os.getenv("SIMULATOR_TYPE", "csv").lower()
    if sim_type == "synthetic":
        from sensors.synthetic_simulator import SyntheticSensorSimulator
        return SyntheticSensorSimulator.fit_from_dataset()
    from sensors.csv_simulator import CSVSensorSimulator
    return CSVSensorSimulator()


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

ws_manager = WebSocketManager()
twin: DigitalTwin | None = None
_ooda_task: asyncio.Task | None = None


async def _ooda_loop(interval_s: float) -> None:
    """Background task: run one OODA tick every interval_s seconds."""
    while True:
        try:
            state = await twin.step()
            payload = twin_state_to_response(state).model_dump()
            await ws_manager.broadcast(payload)
        except Exception as exc:
            print(f"[ERROR] OODA tick failed: {exc}")
        await asyncio.sleep(interval_s)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global twin, _ooda_task

    track_config = _track_config()
    simulator = _build_simulator()
    work_order_client = WorkOrderClient.from_env()

    twin = DigitalTwin(
        track_config=track_config,
        simulator=simulator,
        work_order_client=work_order_client,
    )

    interval = _tick_interval()
    print(f"Starting OODA loop (tick interval: {interval}s, "
          f"track: {track_config}, simulator: {type(simulator).__name__})")
    _ooda_task = asyncio.create_task(_ooda_loop(interval))

    yield

    _ooda_task.cancel()
    try:
        await _ooda_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Rail Track Digital Twin", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/state", response_model=TwinStateResponse)
async def get_state():
    state = twin.get_state()
    if state is None:
        raise HTTPException(status_code=503, detail="No state yet — OODA loop not started")
    return twin_state_to_response(state)


@app.post("/correction")
async def apply_correction(req: CorrectionRequest):
    if req.segment_id < 0 or req.segment_id >= twin.n_segments:
        raise HTTPException(status_code=422, detail=f"segment_id out of range [0, {twin.n_segments - 1}]")
    if req.state not in (0, 1, 2):
        raise HTTPException(status_code=422, detail="state must be 0, 1, or 2")
    twin.apply_human_correction(req.segment_id, req.state)
    return {"ok": True, "segment_id": req.segment_id, "confirmed_state": req.state}


@app.post("/reset")
async def reset():
    twin.reset()
    return {"ok": True}


@app.post("/config")
async def set_config(req: TrackConfigRequest):
    if not req.track_config:
        raise HTTPException(status_code=422, detail="track_config must not be empty")
    if any(s not in (0, 1, 2) for s in req.track_config):
        raise HTTPException(status_code=422, detail="Each segment state must be 0, 1, or 2")
    twin.set_track_config(req.track_config)
    return {"ok": True, "track_config": req.track_config}


@app.get("/config")
async def get_config():
    return {"track_config": twin.track_config}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    # Send the current state immediately on connect so Unreal doesn't wait
    state = twin.get_state()
    if state is not None:
        await ws.send_json(twin_state_to_response(state).model_dump())
    try:
        while True:
            # Keep the connection alive; all sends happen via broadcast()
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)
