"""
Automated Cloudflare Tunnel runner for Aaditya's Accelerator Node.
Spawns 'cloudflared tunnel --url http://localhost:8000', captures the live
*.trycloudflare.com URL, updates mission-control/.env.production locally & on GitHub,
and prepares the environment for 'firebase deploy --only hosting'.
"""

import os
import sys
import re
import shutil
import subprocess
import time
from set_tunnel_url import update_remote_env, update_local_env


def find_cloudflared() -> str:
    """Locates cloudflared binary."""
    # 1. Check PATH
    p = shutil.which("cloudflared")
    if p:
        return p

    # 2. Check current directory or script directory
    for candidate in [
        os.path.join(os.getcwd(), "cloudflared.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe"),
        r"C:\Program Files\cloudflared\cloudflared.exe",
        os.path.expanduser(r"~\cloudflared.exe"),
        os.path.expanduser(r"~\Downloads\cloudflared.exe")
    ]:
        if os.path.exists(candidate):
            return candidate

    return ""


def main():
    print("=" * 70)
    print("  🌐 AADITYA GPU NODE: CLOUDFLARE TUNNEL & FIREBASE SYNC")
    print("=" * 70)

    cloudflared_bin = find_cloudflared()
    if not cloudflared_bin:
        print("[!] cloudflared.exe was not found in PATH or standard folders.")
        print("[*] To install cloudflared on Windows:")
        print("    1. Download from: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe")
        print("    2. Rename it to 'cloudflared.exe' and place it in this folder or in your PATH.")
        print("    3. Or install via winget / scoop:")
        print("       winget install --id Cloudflare.cloudflared")
        print("\n[*] Once installed, re-run this script, or run manually:")
        print("    cloudflared tunnel --url http://localhost:8000")
        print("=" * 70)
        sys.exit(1)

    print(f"[+] Found binary: {cloudflared_bin}")
    print("[*] Launching: cloudflared tunnel --url http://localhost:8000 ...")

    # Cloudflare outputs the tunnel URL to stderr
    proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    try:
        while True:
            line = proc.stderr.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue

            print(f"[cloudflared] {line.strip()}")

            if not tunnel_url:
                match = url_pattern.search(line)
                if match:
                    tunnel_url = match.group(0)
                    print("\n" + "=" * 70)
                    print("  🔥 LIVE CLOUDFLARE TUNNEL ESTABLISHED!")
                    print(f"  Public GPU Node URL: {tunnel_url}")
                    print("=" * 70 + "\n")

                    print("[*] Synchronizing mission-control/.env.production...")
                    update_local_env(tunnel_url)
                    update_remote_env(tunnel_url)

                    print("\n" + "=" * 70)
                    print("  🚀 READY FOR FIREBASE HOSTING DEPLOYMENT!")
                    print("  Run the following commands in mission-control:")
                    print("    1. cd mission-control")
                    print("    2. npm run build")
                    print("    3. cd ..")
                    print("    4. firebase deploy --only hosting")
                    print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n[*] Shutting down Cloudflare tunnel...")
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
