"""Zero-Failure Offline Presentation Playback Server.

Serves the deterministic 45-second high-definition flight simulation sequence:
- WebSocket stream on /ws/telemetry at 30 Hz
- HTTP polling fallback on /api/telemetry/latest (250 ms polling)
- System state endpoint on /api/state
- Interactive injection triggering on /api/inject_seu

Ensures 100% offline demonstration reliability even if Wi-Fi or GPU hardware is unavailable.
"""

import asyncio
import json
import os
import sys
import time
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="RadZero Offline Demo Presentation Server",
    version="1.0.0-OFFLINE",
    description="Deterministic 45-second playback server for live pitch demonstration",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "offline_playback_45s.json")
with open(DATA_PATH, "r") as f:
    TIMELINE_FRAMES = json.load(f)

TOTAL_FRAMES = len(TIMELINE_FRAMES)
current_frame_idx = 0
connected_websockets: Set[WebSocket] = set()
manual_override_state: str = None


@app.on_event("startup")
async def startup_event():
    """Start 30 Hz simulation playback loop."""
    asyncio.create_task(playback_loop())


async def playback_loop():
    """Cycle through 1350 frames (45 seconds) in lock-step 33.3 ms ticks."""
    global current_frame_idx
    fps = 30
    dt = 1.0 / fps

    while True:
        frame_data = TIMELINE_FRAMES[current_frame_idx]
        current_frame_idx = (current_frame_idx + 1) % TOTAL_FRAMES

        if connected_websockets:
            payload = json.dumps(frame_data)
            dead_sockets = set()
            for ws in list(connected_websockets):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_sockets.add(ws)
            connected_websockets.difference_update(dead_sockets)

        await asyncio.sleep(dt)


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """30 Hz real-time WebSocket telemetry stream."""
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Keep socket alive
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        connected_websockets.discard(websocket)


@app.get("/api/telemetry/latest")
async def get_latest_telemetry():
    """HTTP 250 ms polling fallback endpoint."""
    return TIMELINE_FRAMES[current_frame_idx]


@app.get("/api/state")
async def get_system_state():
    """System status and telemetry config."""
    frame_data = TIMELINE_FRAMES[current_frame_idx]
    return {
        "status": frame_data["state"],
        "recovery_count": frame_data["recovery_count"],
        "last_system_latency_ms": frame_data["recovery_latency_system_ms"],
        "last_device_latency_ms": frame_data["recovery_latency_device_ms"],
        "last_breach": frame_data["last_breach"],
        "current_frame": current_frame_idx,
        "total_frames": TOTAL_FRAMES,
        "playback_time_s": frame_data["time_s"],
        "limits": {
            "tau_max": 0.05,
            "alpha_max": 0.02,
            "omega_max": 0.05,
            "delta_t": 0.1,
            "h_max": 0.02,
        },
    }


@app.post("/api/inject_seu")
async def inject_seu_trigger():
    """Jump playback directly to Frame 300 (10.0s - SEU Strike phase)."""
    global current_frame_idx
    current_frame_idx = 300  # Frame 300 = exactly 10.0 seconds
    return {
        "success": True,
        "message": "SEU strike triggered at t=10.0s (Frame 300)",
        "frame": current_frame_idx,
    }


@app.post("/api/trigger_recovery")
async def trigger_recovery_action():
    """Jump playback to Frame 450 (15.0s - In-Situ Recovery phase)."""
    global current_frame_idx
    current_frame_idx = 450
    return {
        "success": True,
        "message": "In-situ recovery triggered at t=15.0s (Frame 450)",
        "frame": current_frame_idx,
    }


if __name__ == "__main__":
    port = 8000
    print(f"\n=======================================================")
    print(f"  RADZERO ZERO-FAILURE OFFLINE PRESENTATION SERVER")
    print(f"  Streaming 45s HD Telemetry Cycle (1350 Frames @ 30 Hz)")
    print(f"  URL: http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
