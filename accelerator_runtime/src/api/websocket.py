"""
30 Hz WebSocket Telemetry Broadcaster (/ws/telemetry).
Streams real-time accelerator metrics, lock contention status, and dual-domain
latency profiling records to connected LAN clients (e.g. Prachi's workstation).

Features:
- Fixed 30 Hz (~33.3ms) non-blocking broadcast loop.
- Graceful disconnect handling (WebSocketDisconnect, ConnectionClosed).
- Concurrent client registry with lock protection.
"""

import asyncio
import json
import time
import logging
from typing import Set, Dict, Any

try:
    from fastapi import WebSocket, WebSocketDisconnect
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    class WebSocket:
        pass
    class WebSocketDisconnect(Exception):
        pass

from ..config import config
from ..runtime.cuda_engine import CUDAExecutionEngine
from ..model.shadow_mirror import HostPinnedShadowMirror
from ..profiling.latency_profiler import DualDomainLatencyProfiler
from ..concurrency.rw_mutex import ReadWriteMutex
from ..runtime.fault_injector import FaultInjectionEngine

logger = logging.getLogger("AcceleratorTelemetry")


class TelemetryBroadcaster:
    """
    Manages client connections and broadcasts 30 Hz real-time telemetry frames.
    """

    def __init__(self,
                 engine: CUDAExecutionEngine,
                 shadow_mirror: HostPinnedShadowMirror,
                 profiler: DualDomainLatencyProfiler,
                 rw_mutex: ReadWriteMutex,
                 injector: FaultInjectionEngine):
        self.engine = engine
        self.shadow_mirror = shadow_mirror
        self.profiler = profiler
        self.rw_mutex = rw_mutex
        self.injector = injector

        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._running = False
        self._broadcast_task: asyncio.Task = None

    async def connect(self, websocket: WebSocket):
        """Accepts and registers incoming client WebSocket."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"Client connected to /ws/telemetry. Active subscribers: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Unregisters disconnected client safely."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"Client disconnected from /ws/telemetry. Active subscribers: {len(self.active_connections)}")

    def build_telemetry_frame(self) -> Dict[str, Any]:
        """Constructs 30 Hz telemetry payload."""
        now_epoch = time.time()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))

        # Lightweight integrity check
        has_fault = self.injector.active_fault is not None

        return {
            "type": "TELEMETRY_FRAME",
            "timestamp": now_iso,
            "epoch_ms": int(now_epoch * 1000),
            "node_name": "Member 3 (Aaditya) RTX 3050 Node",
            "mode": self.engine.current_mode,
            "gpu": self.engine.get_memory_info(),
            "mutex": self.rw_mutex.get_status(),
            "fault": {
                "active": has_fault,
                "details": self.injector.active_fault
            },
            "profiling": {
                "recovery": self.profiler.get_recovery_stats(),
                "inference": self.profiler.get_inference_stats()
            }
        }

    async def _broadcast_loop(self):
        """30 Hz (~33.3ms) periodic broadcast loop."""
        interval = config.telemetry_interval_sec
        logger.info(f"Starting telemetry broadcaster at {config.telemetry_broadcast_hz} Hz ({interval*1000:.1f}ms interval)")

        while self._running:
            t0 = time.perf_counter()

            if self.active_connections:
                payload = self.build_telemetry_frame()
                text_data = json.dumps(payload)

                async with self._lock:
                    clients = list(self.active_connections)

                # Broadcast to all clients concurrently
                dead_clients = []
                for client in clients:
                    try:
                        await client.send_text(text_data)
                    except (WebSocketDisconnect, RuntimeError, Exception) as e:
                        dead_clients.append(client)

                if dead_clients:
                    async with self._lock:
                        for dead in dead_clients:
                            if dead in self.active_connections:
                                self.active_connections.remove(dead)

            # High precision sleep to maintain steady 30 Hz pacing
            elapsed = time.perf_counter() - t0
            sleep_time = max(0.0, interval - elapsed)
            await asyncio.sleep(sleep_time)

    def start(self):
        """Starts broadcaster background task."""
        if not self._running:
            self._running = True
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        """Stops broadcaster and closes active client sockets."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for client in list(self.active_connections):
                try:
                    await client.close()
                except Exception:
                    pass
            self.active_connections.clear()
