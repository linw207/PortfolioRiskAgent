from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any


class FeishuBotClient:
    def send_text(self, webhook_url: str, title: str, content: str, secret: str = "") -> dict[str, Any]:
        if webhook_url.startswith("mock://"):
            return {"ok": True, "dry_run": True, "webhook_url": webhook_url, "title": title}

        payload: dict[str, Any] = {
            "msg_type": "text",
            "content": {"text": f"{title}\n\n{content}"},
        }
        if secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._sign(timestamp, secret)
        request = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return {"ok": False, "status": exc.code, "body": body}
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        code = parsed.get("code", parsed.get("StatusCode", 0))
        return {"ok": code in {0, "0"}, "status": 200, "body": parsed}

    def _sign(self, timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
        digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")


class FeishuCLIClient:
    def status(self) -> dict[str, Any]:
        path = shutil.which("lark-cli")
        if not path:
            return {
                "installed": False,
                "authenticated": False,
                "install_commands": [
                    "npm install -g @larksuite/cli",
                    "npx -y skills add https://open.feishu.cn --skill -y",
                    "lark-cli config init --new",
                    "lark-cli auth login --recommend",
                ],
            }
        try:
            result = subprocess.run(["lark-cli", "auth", "status"], capture_output=True, text=True, timeout=10, check=False)
        except Exception as exc:  # noqa: BLE001
            return {"installed": True, "authenticated": False, "path": path, "error": str(exc)}
        output = (result.stdout + "\n" + result.stderr).strip()
        return {
            "installed": True,
            "authenticated": result.returncode == 0,
            "path": path,
            "returncode": result.returncode,
            "output": output[-1000:],
        }

    def send_text_to_user(self, user_open_id: str, title: str, content: str) -> dict[str, Any]:
        path = shutil.which("lark-cli")
        if not path:
            return {"ok": False, "error": "lark-cli is not installed"}
        message = f"{title}\n\n{content}"
        result = subprocess.run(
            [
                "lark-cli",
                "im",
                "+messages-send",
                "--as",
                "user",
                "--user-id",
                user_open_id,
                "--text",
                message,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode != 0:
            return {"ok": False, "returncode": result.returncode, "output": output[-2000:]}
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"raw": result.stdout.strip()}
        return {"ok": True, "returncode": result.returncode, "body": payload}
