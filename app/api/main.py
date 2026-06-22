from __future__ import annotations

import os
from dataclasses import asdict
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.helpers import detect_language, quick_actions
from app.api.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    ChatRequest,
    ChatResponse,
    SessionResponse,
    SupportCreate,
    SupportResponse,
)
from app.config import load_settings
from app.services.web_request_service import WebRequestService
from app.utils.logging import configure_logging
from bot import build_application

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_widget", "static")


def create_app() -> FastAPI:
    settings = _web_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="AVIDENTIKA Website AI Assistant", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Session-Id"],
        max_age=86400,
    )

    telegram_app = build_application(settings)
    app.state.telegram_app = telegram_app
    app.state.services = telegram_app.bot_data
    app.state.web_requests = WebRequestService(telegram_app.bot_data["db"])

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/session", response_model=SessionResponse)
    async def session(request: Request) -> SessionResponse:
        existing = request.headers.get("X-Session-Id") or request.query_params.get("session_id")
        if existing and 8 <= len(existing) <= 120:
            return SessionResponse(session_id=existing)
        return SessionResponse(session_id=f"web-{uuid4().hex}")

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        data = app.state.services
        if len(payload.message) > data["settings"].max_message_length:
            raise HTTPException(status_code=413, detail="Message is too long")
        if not data["rate_limiter"].allow(_rate_key(payload.session_id)):
            raise HTTPException(status_code=429, detail="Too many requests")
        language = detect_language(payload.message, payload.language)
        answer = await data["ai"].answer(payload.message, language)
        sources = [answer.source_url] if answer.source_url else []
        return ChatResponse(answer=answer.text, sources=sources, quick_actions=quick_actions(language))

    @app.post("/api/appointments", response_model=AppointmentResponse)
    async def appointments(payload: AppointmentCreate, request: Request) -> AppointmentResponse:
        data = app.state.services
        language = detect_language(payload.patient_name, payload.language)
        profile = await app.state.web_requests.upsert_web_profile(
            session_id=payload.session_id,
            language=language,
            patient_name=payload.patient_name,
            telegram_username=payload.telegram_username,
        )
        record = await app.state.web_requests.create_website_appointment(
            profile["id"],
            {**payload.model_dump(), "user_agent": request.headers.get("user-agent")},
        )
        await data["notifications"].notify(data["application"].bot if "application" in data else app.state.telegram_app.bot, "appointment", record, profile)
        return AppointmentResponse(
            public_id=record["public_id"],
            status=record["status"],
            message="Заявка принята. Администратор подтвердит дату и время.",
        )

    @app.post("/api/support", response_model=SupportResponse)
    async def support(payload: SupportCreate, request: Request) -> SupportResponse:
        data = app.state.services
        language = detect_language(payload.question, payload.language)
        profile = await app.state.web_requests.upsert_web_profile(
            session_id=payload.session_id,
            language=language,
            patient_name=payload.patient_name,
            telegram_username=payload.telegram_username,
        )
        record = await app.state.web_requests.create_website_support_request(
            profile["id"],
            {**payload.model_dump(), "user_agent": request.headers.get("user-agent")},
        )
        await data["notifications"].notify(app.state.telegram_app.bot, "support", record, profile)
        return SupportResponse(
            public_id=record["public_id"],
            status=record["status"],
            message="Обращение передано администратору.",
        )

    @app.get("/")
    async def demo() -> FileResponse:
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    return app


def _web_settings() -> SimpleNamespace:
    raw = load_settings()
    values = asdict(raw)
    values.setdefault("google_sheets_enabled", _env_bool("GOOGLE_SHEETS_ENABLED"))
    values.setdefault("google_sheets_web_app_url", os.getenv("GOOGLE_SHEETS_WEB_APP_URL", ""))
    values.setdefault("google_sheets_webhook_secret", os.getenv("GOOGLE_SHEETS_WEBHOOK_SECRET", ""))
    return SimpleNamespace(**values)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on", "да"}


def _rate_key(value: str) -> int:
    return abs(hash(value)) % 2_000_000_000


app = create_app()
