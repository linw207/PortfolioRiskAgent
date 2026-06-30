from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import get_settings


settings = get_settings()
CHROMA_URL = settings.vector.http_url.rstrip("/")
COLLECTIONS = [settings.vector.collection_announcements, settings.vector.collection_memory]


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        CHROMA_URL + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def main() -> None:
    created = []
    existing = []
    for name in COLLECTIONS:
        status, body = request("POST", "/api/v1/collections", {"name": name, "metadata": {"project": "PortfolioRiskAgent"}})
        if status in {200, 201}:
            created.append(name)
        elif status in {409, 500} and "already exists" in body.lower():
            existing.append(name)
        else:
            raise SystemExit(f"failed to create Chroma collection {name}: status={status}, body={body}")
    status, body = request("GET", "/api/v1/collections")
    print(json.dumps({"created": created, "existing": existing, "collections_status": status, "collections": body}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
