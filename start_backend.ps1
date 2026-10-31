# =============================================================================
# RadZero Backend Launch Script
# Starts the radzero telemetry server on 0.0.0.0:8000
# Run this FIRST, then run start_tunnel.ps1 in another terminal
# =============================================================================

$PY = "C:\Users\ADITYA RAJ\AppData\Local\Programs\Python\Python314\python.exe"
$REPO = "C:\Users\ADITYA RAJ\ZOG-AI"

Write-Host "=== RadZero Backend Launcher ===" -ForegroundColor Cyan
Write-Host "Python: $PY"
Write-Host "Repo:   $REPO"
Write-Host ""

# Check Python exists
if (-not (Test-Path $PY)) {
    Write-Host "[ERROR] Python not found at: $PY" -ForegroundColor Red
    exit 1
}

# Check uvicorn is available
$uvicornCheck = & $PY -c "import uvicorn; print('ok')" 2>&1
if ($uvicornCheck -ne "ok") {
    Write-Host "[WARN] uvicorn not installed. Installing now..." -ForegroundColor Yellow
    & $PY -m pip install fastapi "uvicorn[standard]" websockets pydantic numpy python-multipart
}

Write-Host "[OK] Starting radzero telemetry server on 0.0.0.0:8000 ..." -ForegroundColor Green
Write-Host "     WebSocket:  ws://0.0.0.0:8000/ws/telemetry"
Write-Host "     REST API:   http://0.0.0.0:8000/api/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

Set-Location $REPO
& $PY -m uvicorn radzero.telemetry.server:app --host 0.0.0.0 --port 8000 --reload
