"""
Utility to update NEXT_PUBLIC_BACKEND_URL in mission-control/.env.production
both locally and directly on the GitHub repository (gangasagar5928/ZOG-AI).
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

REPO = "gangasagar5928/ZOG-AI"
FILE_PATH = "mission-control/.env.production"


def get_token() -> str:
    """Retrieves GitHub PAT from environment variable or user input."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token and len(sys.argv) > 2:
        token = sys.argv[2]
    return token.strip()


def update_remote_env(tunnel_url: str, token: str):
    """Updates mission-control/.env.production on GitHub via Git Contents API."""
    if not token:
        print("[!] No GitHub token provided. Skipping remote repository update.")
        print("    Set GITHUB_TOKEN environment variable or pass token as second argument.")
        return False

    content = f"NEXT_PUBLIC_BACKEND_URL={tunnel_url}\nNEXT_PUBLIC_FALLBACK_URL={tunnel_url}\n"
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Antigravity-TunnelSync"
    }

    # Fetch current file sha if exists
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sha = data.get("sha")
    except Exception:
        pass

    payload = {
        "message": f"chore(tunnel): set NEXT_PUBLIC_BACKEND_URL to {tunnel_url}",
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"[+] Successfully updated GitHub repository {REPO}!")
            print(f"    File: {FILE_PATH}")
            print(f"    Commit: {res['commit']['sha']}")
            print(f"    URL: https://github.com/{REPO}/commit/{res['commit']['sha']}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[-] GitHub API error ({e.code}): {e.read().decode('utf-8')}")
        return False


def update_local_env(tunnel_url: str):
    """Updates local mission-control/.env.production if directory exists."""
    candidates = [
        os.path.join(os.getcwd(), "mission-control", ".env.production"),
        os.path.join(os.path.dirname(os.getcwd()), "mission-control", ".env.production"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mission-control", ".env.production")
    ]
    for p in candidates:
        if os.path.exists(os.path.dirname(p)):
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"NEXT_PUBLIC_BACKEND_URL={tunnel_url}\nNEXT_PUBLIC_FALLBACK_URL={tunnel_url}\n")
            print(f"[+] Updated local file: {p}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python set_tunnel_url.py <TUNNEL_URL> [GITHUB_TOKEN]")
        print("Example: python set_tunnel_url.py https://radzero-api.trycloudflare.com")
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    token = get_token()
    print(f"[*] Setting backend URL: {url}")
    update_local_env(url)
    update_remote_env(url, token)


if __name__ == "__main__":
    main()
