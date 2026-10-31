"""Tests for FastAPI Telemetry Streaming Service."""

import httpx
import pytest

from radzero.telemetry.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_api_state_endpoint():
    """Verify /api/state returns valid configuration and NOMINAL state."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "limits" in data
        assert data["limits"]["tau_max"] == 0.05
        assert data["limits"]["alpha_max"] == 0.65


@pytest.mark.anyio
async def test_api_telemetry_latest_endpoint():
    """Verify /api/telemetry/latest returns well-formed TelemetryPacket."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/telemetry/latest")
        assert response.status_code == 200
        data = response.json()
        assert "quaternion" in data
        assert len(data["quaternion"]) == 4
        assert "angular_velocity" in data
        assert len(data["angular_velocity"]) == 3
        assert "torque_cmd" in data
        assert len(data["torque_cmd"]) == 3
        assert "block_crcs" in data
        assert len(data["block_crcs"]) == 4


@pytest.mark.anyio
async def test_api_inject_seu_endpoint():
    """Verify /api/inject_seu triggers in-place mutation."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/inject_seu",
            json={"target": "EXPONENT_EXPLODE"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "strike" in data
        assert "mutated_hex" in data["strike"]


@pytest.mark.anyio
async def test_api_reset_endpoint():
    """Verify /api/reset resets system to nominal."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/api/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["status"] == "NOMINAL"
