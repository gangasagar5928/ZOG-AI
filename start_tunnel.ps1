# =============================================================================
# RadZero Cloudflare Tunnel Launcher
# Tunnels http://localhost:8000 to a public trycloudflare.com URL
# Run this AFTER the backend is running (start_backend.ps1)
# =============================================================================

$REPO         = "C:\Users\ADITYA RAJ\ZOG-AI"
$ENV_PROD     = "$REPO\mission-control\.env.production"
$CLOUDFLARED  = "cloudflared"  # Available system-wide via PATH

# Try fallback path if not in PATH
if (-not (Get-Command $CLOUDFLARED -ErrorAction SilentlyContinue)) {
    $CLOUDFLARED = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
}

Write-Host "=== RadZero Cloudflare Tunnel ===" -ForegroundColor Cyan
Write-Host "cloudflared: $CLOUDFLARED"
Write-Host ""

# Verify cloudflared exists
if (-not (Test-Path $CLOUDFLARED) -and -not (Get-Command $CLOUDFLARED -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] cloudflared not found!" -ForegroundColor Red
    Write-Host "Install: winget install --id Cloudflare.cloudflared"
    exit 1
}

# Verify backend is reachable
Write-Host "[CHECK] Verifying backend is running on port 8000..." -ForegroundColor Yellow
$portOpen = (Test-NetConnection -ComputerName localhost -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded
if (-not $portOpen) {
    Write-Host "[WARN] Backend not detected on port 8000. Start start_backend.ps1 first!" -ForegroundColor Yellow
    Write-Host "       Continuing anyway — cloudflared will retry..."
}

Write-Host "[START] Launching cloudflared tunnel for http://localhost:8000 ..." -ForegroundColor Green
Write-Host ""
Write-Host "Watch for a line like:"
Write-Host "  | https://xxxx-xxxx.trycloudflare.com |"
Write-Host ""
Write-Host "Copy that URL, then run:"
Write-Host "  python set_tunnel_url.py https://xxxx-xxxx.trycloudflare.com"
Write-Host "(from inside C:\Users\ADITYA RAJ\ZOG-AI\accelerator_runtime\)"
Write-Host ""

# Run the tunnel — output goes to console so you can grab the URL
& $CLOUDFLARED tunnel --url http://localhost:8000
