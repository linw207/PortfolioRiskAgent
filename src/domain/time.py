from __future__ import annotations

from datetime import datetime, timedelta, timezone


CHINA_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat(timespec="seconds")
