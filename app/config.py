from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when environment configuration is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    admin_chat_id: int
    openai_api_key: str
    openai_model: str
    openai_embedding_model: str
    supabase_url: str
    supabase_service_role_key: str
    log_level: str = "INFO"
    app_env: str = "development"
    rate_limit_requests: int = 10
    rate_limit_period_seconds: int = 60
    max_message_length: int = 1500
    rag_match_threshold: float = 0.72
    rag_match_count: int = 6
    http_timeout_seconds: float = 20.0
    knowledge_base_url: str = "https://avidentika.com.ua/"
    crawl_delay_seconds: float = 1.0
    max_crawl_pages: int = 100


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Не задана обязательная переменная {name}")
    return value


def load_settings(*, env_file: str | None = ".env") -> Settings:
    if env_file:
        load_dotenv(env_file)
    try:
        admin_chat_id = int(_required("ADMIN_CHAT_ID"))
        requests = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
        period = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))
        max_length = int(os.getenv("MAX_MESSAGE_LENGTH", "1500"))
        threshold = float(os.getenv("RAG_MATCH_THRESHOLD", "0.72"))
    except ValueError as exc:
        raise ConfigurationError("Числовые переменные окружения имеют неверный формат") from exc
    if requests < 1 or period < 1 or max_length < 1 or not 0 <= threshold <= 1:
        raise ConfigurationError("Параметры лимитов или RAG находятся вне допустимого диапазона")
    return Settings(
        telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
        admin_chat_id=admin_chat_id,
        openai_api_key=_required("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        supabase_url=_required("SUPABASE_URL"),
        supabase_service_role_key=_required("SUPABASE_SERVICE_ROLE_KEY"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        app_env=os.getenv("APP_ENV", "development"),
        rate_limit_requests=requests,
        rate_limit_period_seconds=period,
        max_message_length=max_length,
        rag_match_threshold=threshold,
        rag_match_count=int(os.getenv("RAG_MATCH_COUNT", "6")),
        http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
        knowledge_base_url=os.getenv("KNOWLEDGE_BASE_URL", "https://avidentika.com.ua/"),
        crawl_delay_seconds=float(os.getenv("CRAWL_DELAY_SECONDS", "1.0")),
        max_crawl_pages=int(os.getenv("MAX_CRAWL_PAGES", "100")),
    )
