from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from app.models.schemas import AppointmentInput, SupportInput

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    pass


class SupabaseService:
    def __init__(self, url: str | None = None, key: str | None = None, *, client: Client | Any | None = None) -> None:
        self.client = client if client is not None else create_client(str(url), str(key))

    async def _execute(self, builder: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await asyncio.to_thread(builder.execute)
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2 ** attempt))
        logger.error("Supabase operation failed after retries: %s", type(last_error).__name__)
        raise DatabaseError("Database operation failed") from last_error

    async def upsert_profile(self, telegram_user: Any, language: str) -> dict[str, Any]:
        payload = {
            "telegram_user_id": telegram_user.id,
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "preferred_language": language,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = await self._execute(
            self.client.table("profiles").upsert(payload, on_conflict="telegram_user_id").select("id").limit(1)
        )
        if not result.data:
            raise DatabaseError("Profile was not returned")
        return result.data[0]

    async def create_appointment(self, profile_id: str, value: AppointmentInput) -> dict[str, Any]:
        payload = value.to_record(profile_id)
        payload["public_id"] = f"A-{uuid4().hex[:8].upper()}"
        result = await self._execute(self.client.table("appointments").insert(payload).select("*").limit(1))
        if not result.data:
            raise DatabaseError("Appointment was not created")
        logger.info("Appointment created: %s", payload["public_id"])
        return result.data[0]

    async def create_support_request(self, profile_id: str, value: SupportInput) -> dict[str, Any]:
        payload = value.to_record(profile_id)
        payload["public_id"] = f"S-{uuid4().hex[:8].upper()}"
        result = await self._execute(self.client.table("support_requests").insert(payload).select("*").limit(1))
        if not result.data:
            raise DatabaseError("Support request was not created")
        logger.info("Support request created: %s", payload["public_id"])
        return result.data[0]

    async def update_request_status(
        self, kind: str, public_id: str, status: str, admin_telegram_id: int
    ) -> dict[str, Any]:
        if kind not in {"appointment", "support"} or status not in {"in_progress", "closed", "cancelled"}:
            raise ValueError("Unsupported request type or status")
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "status": status,
            "assigned_admin_telegram_id": admin_telegram_id,
            "updated_at": now,
        }
        if status in {"closed", "cancelled"}:
            payload["closed_at"] = now
        table = "appointments" if kind == "appointment" else "support_requests"
        result = await self._execute(
            self.client.table(table).update(payload).eq("public_id", public_id).select("*").limit(1)
        )
        if not result.data:
            raise DatabaseError("Request was not found")
        logger.info("Request status changed: %s -> %s", public_id, status)
        return result.data[0]

    async def save_conversation(
        self, profile_id: str, role: str, message: str, language: str, source_urls: list[str] | None = None
    ) -> None:
        # Store only short administrative Q&A; never persist long free-form medical narratives.
        safe_message = message[:1000]
        await self._execute(self.client.table("conversations").insert({
            "user_id": profile_id,
            "role": role,
            "message": safe_message,
            "language": language,
            "source_urls": source_urls or [],
        }))
