from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.utils.phone import normalize_ua_phone

logger = logging.getLogger(__name__)


class WebRequestService:
    """Website-facing persistence layer built on top of the existing Supabase client."""

    def __init__(self, supabase_service: Any) -> None:
        self.db = supabase_service
        self.client = supabase_service.client
        self.sheets = getattr(supabase_service, "sheets", None)

    async def _execute(self, builder: Any) -> Any:
        if hasattr(self.db, "_execute"):
            return await self.db._execute(builder)
        return await asyncio.to_thread(builder.execute)

    async def upsert_web_profile(
        self,
        *,
        session_id: str,
        language: str,
        patient_name: str | None = None,
        telegram_username: str | None = None,
    ) -> dict[str, Any]:
        language = language if language in {"uk", "ru"} else "uk"
        now = datetime.now(UTC).isoformat()
        payload = {
            "web_session_id": session_id,
            "telegram_user_id": None,
            "username": _clean_username(telegram_username),
            "first_name": patient_name[:80] if patient_name else None,
            "preferred_language": language,
            "updated_at": now,
        }
        result = await self._execute(
            self.client.table("profiles")
            .upsert(payload, on_conflict="web_session_id")
            .select("id,web_session_id,username,preferred_language")
        )
        if not result.data:
            raise RuntimeError("Web profile was not returned")
        return result.data[0]

    async def create_website_appointment(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any]:
        phone = normalize_ua_phone(data.get("phone") or "")
        if not phone:
            raise ValueError("Invalid Ukrainian phone number")
        payload = {
            "public_id": f"A-{uuid4().hex[:8].upper()}",
            "user_id": profile_id,
            "status": "new",
            "source": "website",
            "patient_name": (data.get("patient_name") or "").strip()[:80],
            "phone": phone,
            "telegram_username": _clean_username(data.get("telegram_username")),
            "service": (data.get("service") or "").strip()[:200],
            "preferred_date": _optional(data.get("preferred_date"), 80),
            "preferred_time": _optional(data.get("preferred_time"), 80),
            "doctor": _optional(data.get("doctor"), 120),
            "comment": _optional(data.get("comment"), 500),
            "web_session_id": data.get("session_id"),
            "contact_method": _optional(data.get("contact_method"), 40) or "phone",
            "created_from_url": _optional(data.get("created_from_url"), 500),
            "user_agent": _optional(data.get("user_agent"), 300),
        }
        result = await self._execute(self.client.table("appointments").insert(payload).select("*"))
        if not result.data:
            raise RuntimeError("Appointment was not created")
        record = result.data[0]
        logger.info("Website appointment created: %s", record.get("public_id"))
        if self.sheets:
            await self.sheets.sync_appointment(record, "Заявка с сайта")
        return record

    async def create_website_support_request(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any]:
        phone = normalize_ua_phone(data.get("phone") or "")
        if not phone:
            raise ValueError("Invalid Ukrainian phone number")
        payload = {
            "public_id": f"S-{uuid4().hex[:8].upper()}",
            "user_id": profile_id,
            "status": "new",
            "source": "website",
            "patient_name": (data.get("patient_name") or "").strip()[:80],
            "phone": phone,
            "telegram_username": _clean_username(data.get("telegram_username")),
            "question": (data.get("question") or "").strip()[:1000],
            "web_session_id": data.get("session_id"),
            "contact_method": _optional(data.get("contact_method"), 40) or "phone",
            "created_from_url": _optional(data.get("created_from_url"), 500),
            "user_agent": _optional(data.get("user_agent"), 300),
        }
        result = await self._execute(self.client.table("support_requests").insert(payload).select("*"))
        if not result.data:
            raise RuntimeError("Support request was not created")
        record = result.data[0]
        logger.info("Website support request created: %s", record.get("public_id"))
        if self.sheets:
            await self.sheets.append_history(record, "Обращение с сайта")
        return record


def _optional(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _clean_username(value: Any) -> str | None:
    text = _optional(value, 64)
    if not text:
        return None
    return text.lstrip("@")
