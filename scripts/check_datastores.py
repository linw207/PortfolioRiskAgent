from __future__ import annotations

import json
import socket
import subprocess
import urllib.request


def tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def command_check(command: list[str]) -> dict:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=5)
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def http_check(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return {"ok": True, "url": url, "status": response.status, "body": parsed}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}


def main() -> None:
    checks = {
        "mongo_tcp_27017": tcp_check("127.0.0.1", 27017),
        "mongo_ping": command_check(["mongosh", "--quiet", "--eval", "db.adminCommand({ ping: 1 })"]),
        "mongo_collections": command_check(
            [
                "mongosh",
                "--quiet",
                "portfolio_risk_agent",
                "--eval",
                "db.getCollectionNames().sort().join(',')",
            ]
        ),
        "redis_tcp_6379": tcp_check("127.0.0.1", 6379),
        "redis_ping": command_check(["docker", "exec", "pra-redis", "redis-cli", "ping"]),
        "redis_initialized": command_check(["docker", "exec", "pra-redis", "redis-cli", "GET", "pra:system:initialized"]),
        "chroma_v1_heartbeat": http_check("http://127.0.0.1:8001/api/v1/heartbeat"),
        "chroma_collections": http_check("http://127.0.0.1:8001/api/v1/collections"),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
