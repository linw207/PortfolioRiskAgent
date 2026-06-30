from __future__ import annotations

import json
from typing import Any

from config.settings import RedisSettings
from src.domain.entity import AnalysisTask
from src.infra.repo.encoder_decoder import encode
from src.infra.repo.redis import RedisClientProvider


class RedisRuntimeService:
    def __init__(self, settings: RedisSettings, redis: RedisClientProvider) -> None:
        self.settings = settings
        self.redis = redis

    def save_task_status(self, task: AnalysisTask) -> None:
        key = self.task_status_key(task.task_id)
        self.redis.set_value(key, json.dumps(encode(task), ensure_ascii=False), ex=86400)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        raw = self.redis.get_value(self.task_status_key(task_id))
        return json.loads(raw) if raw else None

    def enqueue_analysis_task(self, task_id: str) -> int:
        return self.redis.lpush(self.analysis_queue_key(), task_id)

    def pop_analysis_task(self) -> str | None:
        return self.redis.rpop(self.analysis_queue_key())

    def analysis_queue_size(self) -> int:
        return self.redis.llen(self.analysis_queue_key())

    def acquire_schedule_lock(self, job_type: str, target_id: str, ttl_seconds: int = 3600) -> bool:
        return self.redis.set_value(self.schedule_lock_key(job_type, target_id), "1", ex=ttl_seconds, nx=True)

    def release_schedule_lock(self, job_type: str, target_id: str) -> int:
        return self.redis.delete(self.schedule_lock_key(job_type, target_id))

    def task_status_key(self, task_id: str) -> str:
        return f"{self.settings.key_prefix}:task:{task_id}:status"

    def analysis_queue_key(self) -> str:
        return f"{self.settings.key_prefix}:queue:analysis"

    def schedule_lock_key(self, job_type: str, target_id: str) -> str:
        return f"{self.settings.key_prefix}:lock:schedule:{job_type}:{target_id}"
