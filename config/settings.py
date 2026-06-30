from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class HttpServerSettings:
    host: str = field(default_factory=lambda: os.getenv("HTTP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("HTTP_PORT", "8000")))


@dataclass(frozen=True, slots=True)
class MongoSettings:
    uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    database: str = field(default_factory=lambda: os.getenv("MONGODB_DATABASE", "portfolio_risk_agent"))
    connect_timeout_ms: int = field(default_factory=lambda: int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "800")))
    enabled: bool = field(default_factory=lambda: _bool("MONGODB_ENABLED", True))


@dataclass(frozen=True, slots=True)
class RedisSettings:
    url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    enabled: bool = field(default_factory=lambda: _bool("REDIS_ENABLED", True))
    key_prefix: str = field(default_factory=lambda: os.getenv("REDIS_KEY_PREFIX", "pra"))


@dataclass(frozen=True, slots=True)
class VectorSettings:
    provider: str = field(default_factory=lambda: os.getenv("VECTOR_PROVIDER", "chroma"))
    mode: str = field(default_factory=lambda: os.getenv("VECTOR_MODE", "http"))
    http_url: str = field(default_factory=lambda: os.getenv("CHROMA_HTTP_URL", "http://127.0.0.1:8001"))
    persist_dir: str = field(default_factory=lambda: os.getenv("VECTOR_PERSIST_DIR", "./data/vector/chroma"))
    collection_announcements: str = field(default_factory=lambda: os.getenv("VECTOR_COLLECTION_ANNOUNCEMENTS", "announcement_chunks"))
    collection_memory: str = field(default_factory=lambda: os.getenv("VECTOR_COLLECTION_MEMORY", "agent_memory"))
    allow_embedding_fallback: bool = field(default_factory=lambda: _bool("VECTOR_ALLOW_EMBEDDING_FALLBACK", False))
    enabled: bool = field(default_factory=lambda: _bool("VECTOR_ENABLED", True))


@dataclass(frozen=True, slots=True)
class ModelSettings:
    provider: str = field(default_factory=lambda: os.getenv("MODEL_PROVIDER", "ollama"))
    base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://192.168.2.43:11434"))
    model_name: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))
    embedding_model_name: str = field(default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:4b"))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("MODEL_TIMEOUT_SECONDS", "8")))
    temperature: float = field(default_factory=lambda: float(os.getenv("MODEL_TEMPERATURE", "0.2")))
    max_agent_steps: int = field(default_factory=lambda: int(os.getenv("MAX_AGENT_STEPS", "6")))
    max_context_chars: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_CHARS", "12000")))
    tool_retry_times: int = field(default_factory=lambda: int(os.getenv("TOOL_RETRY_TIMES", "1")))


@dataclass(frozen=True, slots=True)
class SearchSettings:
    backend: str = field(default_factory=lambda: os.getenv("SEARCH_BACKEND", "hybrid"))
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    serpapi_api_key: str = field(default_factory=lambda: os.getenv("SERPAPI_API_KEY", ""))
    max_results: int = field(default_factory=lambda: int(os.getenv("SEARCH_MAX_RESULTS", "5")))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("SEARCH_TIMEOUT_SECONDS", "8")))
    trusted_news_domains: tuple[str, ...] = (
        "cs.com.cn",
        "cnstock.com",
        "stcn.com",
        "证券时报",
        "中国证券报",
        "上海证券报",
    )
    trusted_announcement_domains: tuple[str, ...] = (
        "cninfo.com.cn",
        "sse.com.cn",
        "szse.cn",
        "csrc.gov.cn",
    )


@dataclass(frozen=True, slots=True)
class MarketDataSettings:
    provider_order: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            item.strip().lower()
            for item in os.getenv("MARKET_DATA_PROVIDER_ORDER", "itick,akshare,sample").split(",")
            if item.strip()
        )
    )
    itick_api_token: str = field(default_factory=lambda: os.getenv("ITICK_API_TOKEN", ""))
    itick_base_url: str = field(default_factory=lambda: os.getenv("ITICK_BASE_URL", "https://api.itick.org"))
    itick_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("ITICK_TIMEOUT_SECONDS", "5")))
    realtime_cache_ttl_seconds: float = field(default_factory=lambda: float(os.getenv("REALTIME_QUOTE_CACHE_TTL_SECONDS", "3")))


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_name: str = "PortfolioRiskAgent"
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    use_memory_fallback: bool = field(default_factory=lambda: _bool("USE_MEMORY_FALLBACK", True))
    http: HttpServerSettings = field(default_factory=HttpServerSettings)
    mongo: MongoSettings = field(default_factory=MongoSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    vector: VectorSettings = field(default_factory=VectorSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    market_data: MarketDataSettings = field(default_factory=MarketDataSettings)


def get_settings() -> AppSettings:
    return AppSettings()
