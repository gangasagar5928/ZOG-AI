"""FastAPI Telemetry Streaming Server.

Broadcasts 30 Hz JSON telemetry over WebSockets (/ws/telemetry) to Next.js Mission Control dashboard.
Provides 250 ms HTTP polling fallback (/api/telemetry/latest) and SEU fault injection control endpoints.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import List, Optional, Set
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel

from radzero.core.types import BitfieldTarget, KinematicLimits, SystemState, TelemetryPacket
from radzero.mutation.ieee754_injector import IEEE754Injector
from radzero.recovery.state_machine import RadZeroRuntimeSentinel

from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("radzero.telemetry")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Launch and cleanly cancel asynchronous vehicle simulation loop."""
    sim_task = asyncio.create_task(_simulation_loop())
    yield
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="RadZero Mission Control Telemetry API",
    version="2.3.0-FROZEN",
    description="Real-time telemetry and SEU fault-injection sentinel for Edge AI ADCS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global runtime sentinel instance and shared state
limits = KinematicLimits()
sentinel = RadZeroRuntimeSentinel(limits=limits)
latest_packet: Optional[TelemetryPacket] = None
connected_websockets: Set[WebSocket] = set()

# Simulated spacecraft state: [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z]
current_state = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.003, 0.008], dtype=np.float64)


class InjectSEURequest(BaseModel):
    layer: Optional[str] = None
    target: str = "EXPONENT_EXPLODE"  # SIGN, EXPONENT_EXPLODE, EXPONENT_COLLAPSE, MANTISSA


class CorruptMirrorRequest(BaseModel):
    param_name: str = "block0.weight"
    corrupt_backup: bool = True


async def _simulation_loop():
    """Continuous spacecraft orbit simulation synchronized with 100 ms control frame."""
    global current_state, latest_packet

    dt = limits.delta_t  # 100 ms control frame
    while True:
        try:
            # Step the sentinel with current vehicle kinematic state
            packet = sentinel.step(current_state)
            latest_packet = packet

            # Advance kinematics: integrate angular velocity using commanded torque
            tau_cmd = np.array(packet.torque_cmd, dtype=np.float64)
            omega = current_state[4:7]

            # Euler rotation: I * d_omega = tau - omega x (I * omega) + small external perturbation
            i_w = limits.inertia_matrix @ omega
            gyro = np.cross(omega, i_w)
            # Add small random gravity-gradient / aerodynamic disturbance torque
            disturbance = np.random.normal(0.0, 1e-4, size=3)
            alpha = limits.inv_inertia @ (tau_cmd - gyro + disturbance)

            # Integrate angular velocity: omega_{k+1} = omega_k + alpha * dt
            new_omega = omega + alpha * dt

            # Quaternion kinematic integration: q_dot = 0.5 * Omega(omega) * q
            q = current_state[:4]
            wx, wy, wz = new_omega
            omega_matrix = np.array([
                [0.0, -wx, -wy, -wz],
                [wx, 0.0, wz, -wy],
                [wy, -wz, 0.0, wx],
                [wz, wy, -wx, 0.0]
            ], dtype=np.float64)
            q_dot = 0.5 * (omega_matrix @ q)
            new_q = q + q_dot * dt
            new_q /= np.linalg.norm(new_q)  # Normalize quaternion

            current_state = np.concatenate([new_q, new_omega])

            # Broadcast to all connected WebSockets
            if connected_websockets:
                telemetry_json = json.dumps(packet.to_dict())
                dead_sockets = set()
                for ws in list(connected_websockets):
                    try:
                        await ws.send_text(telemetry_json)
                    except Exception:
                        dead_sockets.add(ws)
                connected_websockets.difference_update(dead_sockets)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry loop simulation error: {e}", exc_info=True)
            sentinel.state = SystemState.DEGRADED
            sentinel.last_breach_msg = f"Telemetry exception: {e}"

        await asyncio.sleep(dt)


@app.get("/api/health")
async def get_health():
    """Health check endpoint."""
    return {"status": "ok", "state": sentinel.state.value}


@app.get("/api/telemetry/latest")
async def get_latest_telemetry():
    """HTTP 250 ms polling fallback endpoint for telemetry data."""
    if latest_packet is None:
        pkt = sentinel.step(current_state)
        return pkt.to_dict()
    return latest_packet.to_dict()


@app.get("/api/state")
async def get_system_state():
    """Return runtime sentinel state and configuration."""
    return {
        "status": sentinel.state.value,
        "recovery_count": sentinel.recovery_count,
        "last_system_latency_ms": sentinel.last_system_latency_ms,
        "last_device_latency_ms": sentinel.last_device_latency_ms,
        "last_breach": sentinel.last_breach_msg,
        "limits": {
            "tau_max": limits.tau_max,
            "alpha_max": limits.alpha_max,
            "omega_max": limits.omega_max,
            "delta_t": limits.delta_t,
            "h_max": limits.h_max,
        },
    }


@app.post("/api/inject_seu")
async def inject_seu(req: InjectSEURequest):
    """Simulate in-flight cosmic ray SEU bit-mutation into PyTorch graph memory."""
    target_enum = BitfieldTarget(req.target.upper())
    strike = IEEE754Injector.inject(
        sentinel.model,
        layer_name=req.layer,
        target=target_enum,
    )
    return {
        "success": True,
        "strike": {
            "layer": strike.layer_name,
            "bitfield_target": strike.bitfield_target.value,
            "bit_index": strike.bit_index,
            "original_float": strike.original_float,
            "mutated_float": strike.mutated_float,
            "original_hex": strike.original_hex,
            "mutated_hex": strike.mutated_hex,
        },
    }


@app.post("/api/corrupt_mirror")
async def corrupt_mirror(req: CorruptMirrorRequest):
    """Intentionally corrupt shadow mirrors to test SAFE_HOLD escalation."""
    sentinel.mirror.corrupt_mirror_for_testing(req.param_name, corrupt_backup=False)
    if req.corrupt_backup:
        sentinel.mirror.corrupt_mirror_for_testing(req.param_name, corrupt_backup=True)
    return {"success": True, "message": f"Corrupted shadow mirrors for {req.param_name}"}


@app.post("/api/reset")
async def reset_nominal():
    """Reset sentinel and attitude state back to nominal baseline."""
    global current_state
    current_state = np.array([1.0, 0.0, 0.0, 0.0, 0.005, -0.003, 0.008], dtype=np.float64)
    sentinel.reset_nominal()
    return {"success": True, "status": sentinel.state.value}


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """WebSocket stream transmitting 30 Hz JSON telemetry packets."""
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Keep-alive receive ping/pong or client command
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.discard(websocket)
    except Exception:
        connected_websockets.discard(websocket)

@app.get("/logo.png")
async def get_logo():
    """Serve RadZero mission emblem logo."""
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "assets", "logo.png"
    )
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    return {"error": "Logo not found"}

