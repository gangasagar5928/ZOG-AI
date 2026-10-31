"""
FastAPI Server Setup & LAN Distribution Engine.
Binds to 0.0.0.0:8000 to enable LAN access from Prachi's laptop and other nodes.
Equipped with CORS, lifespan handlers, REST router, 30 Hz WebSocket broadcaster,
and embedded real-time web dashboard.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    class FastAPI:
        def __init__(self, *args, **kwargs): pass
    class HTMLResponse: pass
    class JSONResponse: pass

from ..config import config, OperationalMode
from ..concurrency.rw_mutex import ReadWriteMutex
from ..model.member1_model import create_or_load_member1_model
from ..model.shadow_mirror import HostPinnedShadowMirror
from ..profiling.latency_profiler import DualDomainLatencyProfiler
from ..runtime.cuda_engine import CUDAExecutionEngine
from ..runtime.recovery_barrier import HardwareRecoveryBarrier
from ..runtime.fault_injector import FaultInjectionEngine
from .routes import create_router
from .websocket import TelemetryBroadcaster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("AcceleratorServer")


class RuntimeContainer:
    """Singleton container holding initialized runtime subsystems."""
    def __init__(self):
        logger.info("Initializing Member 1 PyTorch Perception Model...")
        self.model = create_or_load_member1_model()

        logger.info("Initializing Read-Write Parameter Mutex...")
        self.rw_mutex = ReadWriteMutex("ParamMutex_RTX3050")

        logger.info("Initializing Host-Pinned Memory Shadow Mirror (pin_memory=True)...")
        self.shadow_mirror = HostPinnedShadowMirror(
            self.model,
            pin_memory=config.pin_host_memory
        )

        logger.info("Initializing Dual-Domain Latency Profiler...")
        self.profiler = DualDomainLatencyProfiler()

        logger.info("Initializing CUDA Execution Engine (Streams & Device Context)...")
        self.engine = CUDAExecutionEngine(self.model, self.rw_mutex)

        logger.info("Initializing Hardware Recovery Barrier (In-Place DMA Copy)...")
        self.barrier = HardwareRecoveryBarrier(
            self.engine,
            self.shadow_mirror,
            self.rw_mutex,
            self.profiler
        )

        logger.info("Initializing Hardware Fault Injection Subsystem...")
        self.injector = FaultInjectionEngine(self.engine, self.rw_mutex)

        self.broadcaster = TelemetryBroadcaster(
            self.engine,
            self.shadow_mirror,
            self.profiler,
            self.rw_mutex,
            self.injector
        )


# Global singleton instance
_container_instance: Optional[RuntimeContainer] = None


def get_runtime_container() -> RuntimeContainer:
    global _container_instance
    if _container_instance is None:
        _container_instance = RuntimeContainer()
    return _container_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for FastAPI application."""
    container = get_runtime_container()
    logger.info("Booting Accelerator Runtime Container...")

    # Start 30 Hz WebSocket Telemetry Broadcaster
    container.broadcaster.start()

    # Background nominal inference task to simulate live processing
    async def nominal_inference_loop():
        logger.info("Started background nominal inference loop...")
        while True:
            try:
                if container.engine.current_mode in (OperationalMode.NOMINAL, OperationalMode.BENCHMARK):
                    _, infer_ms = container.engine.execute_inference()
                    container.profiler.register_inference(infer_ms)
                await asyncio.sleep(0.05)  # ~20 FPS background inference
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background inference: {e}")
                await asyncio.sleep(0.2)

    infer_task = asyncio.create_task(nominal_inference_loop())

    yield

    logger.info("Shutting down Accelerator Runtime...")
    infer_task.cancel()
    await container.broadcaster.stop()


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title="Accelerator Runtime & Systems Integration API",
        description="Member 3 (Aaditya) RTX 3050 CUDA Acceleration & Resilient DMA Recovery Service",
        version="1.0.0",
        lifespan=lifespan
    )

    # Enable full CORS for LAN access (e.g. Prachi's laptop)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # WebSocket Telemetry Broadcaster (30 Hz)
    @app.websocket("/ws/telemetry")
    async def websocket_telemetry_endpoint(websocket: WebSocket):
        container = get_runtime_container()
        await container.broadcaster.connect(websocket)
        try:
            while True:
                # Keep socket alive and listen for client pings
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await container.broadcaster.disconnect(websocket)
        except Exception as e:
            logger.warning(f"WebSocket client disconnected/error: {e}")
            await container.broadcaster.disconnect(websocket)

    # Embedded Real-Time HUD Dashboard Endpoint
    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        dashboard_html_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..", "dashboard", "index.html"
        )
        if os.path.exists(dashboard_html_path):
            with open(dashboard_html_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<h3>Accelerator Runtime HUD Dashboard</h3><p>API is running on 0.0.0.0:8000</p>"

    # Attach REST router
    container = get_runtime_container()
    router = create_router(
        container.engine,
        container.barrier,
        container.injector,
        container.shadow_mirror,
        container.profiler,
        container.rw_mutex
    )
    app.include_router(router)

    return app
