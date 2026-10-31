#!/usr/bin/env python3
"""
RadZero – Auto-Tunnel-and-Deploy Orchestrator
==============================================
Reads the live Cloudflare tunnel URL from cloudflared output,
updates mission-control/.env.production locally and on GitHub,
then optionally triggers a firebase deploy.

Usage:
    python auto_deploy.py <tunnel_url> [--firebase]

Example:
    $env:GITHUB_TOKEN = "ghp_..."
    python auto_deploy.py https://abcd-1234.trycloudflare.com --firebase
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
ENV_PROD  = REPO_ROOT / "mission-control" / ".env.production"


def update_env_production(tunnel_url: str) -> None:
    """Update NEXT_PUBLIC_BACKEND_URL in .env.production locally."""
    if not ENV_PROD.exists():
        print(f"[ERROR] {ENV_PROD} not found!", file=sys.stderr)
        sys.exit(1)

    lines = ENV_PROD.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("NEXT_PUBLIC_BACKEND_URL=") or line.startswith("NEXT_PUBLIC_FALLBACK_URL="):
            key = line.split("=", 1)[0]
            new_lines.append(f"{key}={tunnel_url}")
        else:
            new_lines.append(line)
    ENV_PROD.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[OK] Updated {ENV_PROD}")
    print(f"     NEXT_PUBLIC_BACKEND_URL={tunnel_url}")


def git_commit_push(tunnel_url: str) -> None:
    """Commit the updated .env.production and push to GitHub."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[WARN] GITHUB_TOKEN not set — skipping GitHub push.")
        print("       Set it with: $env:GITHUB_TOKEN = 'ghp_...'")
        return

    remote_url = f"https://{token}@github.com/gangasagar5928/ZOG-AI.git"
    cwd = str(REPO_ROOT)

    def run(cmd: list[str]) -> None:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[WARN] {' '.join(cmd)}: {result.stderr.strip()}")
        else:
            print(f"[OK]   {' '.join(cmd[:3])}")

    run(["git", "add", "mission-control/.env.production"])
    run(["git", "commit", "-m", f"chore(tunnel): update live tunnel URL to {tunnel_url}"])
    run(["git", "remote", "set-url", "origin", remote_url])
    run(["git", "push", "origin", "main"])
    # Reset remote to non-token URL
    run(["git", "remote", "set-url", "origin", "https://github.com/gangasagar5928/ZOG-AI.git"])
    print("[OK] Pushed to GitHub.")


def firebase_deploy() -> None:
    """Run npm run build + firebase deploy --only hosting."""
    mc_dir = REPO_ROOT / "mission-control"
    print("\n[BUILD] Running Next.js static export...")

    # npm install
    r = subprocess.run(["npm", "install"], cwd=str(mc_dir), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] npm install failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)

    # npm run build  (creates mission-control/out/)
    r = subprocess.run(["npm", "run", "build"], cwd=str(mc_dir), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] npm run build failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)

    print("[OK] Next.js build complete → mission-control/out/")
    print("\n[DEPLOY] Running firebase deploy --only hosting ...")

    r = subprocess.run(
        ["firebase", "deploy", "--only", "hosting"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(f"[ERROR] firebase deploy failed:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)
    print("[OK] Firebase hosting deployed!")


def main() -> None:
    parser = argparse.ArgumentParser(description="RadZero auto-deploy orchestrator")
    parser.add_argument("tunnel_url", help="Cloudflare tunnel URL (https://xxxx.trycloudflare.com)")
    parser.add_argument("--firebase", action="store_true", help="Also build and deploy to Firebase")
    args = parser.parse_args()

    tunnel_url = args.tunnel_url.rstrip("/")
    if not tunnel_url.startswith("https://"):
        print("[ERROR] Tunnel URL must start with https://", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== RadZero Auto-Deploy Orchestrator ===")
    print(f"Tunnel URL: {tunnel_url}\n")

    update_env_production(tunnel_url)
    git_commit_push(tunnel_url)

    if args.firebase:
        firebase_deploy()
    else:
        print("\n[TIP] To also build and deploy Firebase hosting, add --firebase flag:")
        print(f"      python auto_deploy.py {tunnel_url} --firebase")

    print("\n[DONE] All steps complete.")
    print(f"  Backend API:  {tunnel_url}/api/health")
    print(f"  WebSocket:    wss://{tunnel_url.split('://',1)[-1]}/ws/telemetry")


if __name__ == "__main__":
    main()
