from __future__ import annotations

import json
from typing import Any


def parse_json_action(text: str) -> dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.strip("`").strip()
        if payload.startswith("json"):
            payload = payload[4:].strip()
    data = json.loads(payload)
    missing = [key for key in ("思考", "动作", "参数") if key not in data]
    if missing:
        raise ValueError(f"JSON Action 缺少字段: {', '.join(missing)}")
    if not isinstance(data["参数"], dict):
        raise ValueError("JSON Action 参数必须是对象")
    return data
