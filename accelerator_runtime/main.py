"""
Accelerator Runtime Service Entrypoint.
Member 3 (Aaditya): Accelerator Runtime (CUDA) & Systems Integration Lead.
Hardware Target: Dedicated GPU Acceleration Node (NVIDIA RTX 3050 Mobile, CUDA 12.x).

Hosts FastAPI application on 0.0.0.0:8000 for LAN distribution to Prachi's workstation.
"""

import sys
import socket
import argparse
import logging
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Aaditya-Node] %(message)s"
)
logger = logging.getLogger("AcceleratorRuntime")


def get_lan_ip() -> str:
    """Discovers host LAN IP address for cross-node connectivity."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually establish connection
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    parser = argparse.ArgumentParser(description="Aaditya RTX 3050 Accelerator Runtime & Systems Integration Node")
    parser.add_argument("--host", default=config.host, help=f"Host network interface bind (default: {config.host})")
    parser.add_argument("--port", type=int, default=config.port, help=f"Port number (default: {config.port})")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU execution mode for emulation")
    args = parser.parse_args()

    if args.force_cpu:
        config.force_cpu = True

    lan_ip = get_lan_ip()

    print("=" * 75)
    print("  🚀 MEMBER 3 (AADITYA): ACCELERATOR RUNTIME (CUDA) & SYSTEMS INTEGRATION")
    print("=" * 75)
    print(f"  Target Hardware  : {config.device_name} (RTX 3050 Mobile, CUDA 12.x)")
    print(f"  Network Bind     : {args.host}:{args.port}")
    print(f"  LAN Access URL   : http://{lan_ip}:{args.port}/ (Prachi's connection endpoint)")
    print(f"  WebSocket Stream : ws://{lan_ip}:{args.port}/ws/telemetry (30 Hz)")
    print(f"  REST API Docs    : http://{lan_ip}:{args.port}/docs (Swagger UI)")
    print("=" * 75)

    try:
        import uvicorn
        uvicorn.run(
            "src.api.server:create_app",
            host=args.host,
            port=args.port,
            factory=True,
            log_level="info",
            access_log=False
        )
    except ImportError:
        logger.error("uvicorn is not installed in the active environment.")
        logger.info("Please install dependencies: pip install fastapi uvicorn websockets torch")
        sys.exit(1)


if __name__ == "__main__":
    main()
