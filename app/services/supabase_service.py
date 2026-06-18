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
            self.client.table("profiles").upsert(payload, on_conflict="telegram_user_id").select("id")
        )
        if not result.data:
            raise DatabaseError("Profile was not returned")
        return result.data[0]

    async def create_appointment(self, profile_id: str, value: AppointmentInput) -> dict[str, Any]:
        payload = value.to_record(profile_id)
        payload["public_id"] = f"A-{uuid4().hex[:8].upper()}"
        result = await self._execute(self.client.table("appointments").insert(payload).select("*"))
        if not result.data:
            raise DatabaseError("Appointment was not created")
        logger.info("Appointment created: %s", payload["public_id"])
        return result.data[0]

    async def create_support_request(self, profile_id: str, value: SupportInput) -> dict[str, Any]:
        payload = value.to_record(profile_id)
        payload["public_id"] = f"S-{uuid4().hex[:8].upper()}"
        result = await self._execute(self.client.table("support_requests").insert(payload).select("*"))
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
            self.client.table(table).update(payload).eq("public_id", public_id).select("*")
        )
        if not result.data:
            raise DatabaseError("Request was not found")
        logger.info("Request status changed: %s -> %s", public_id, status)
        return result.data[0]

    async def get_profile_notification_target(self, profile_id: str) -> dict[str, Any]:
        result = await self._execute(
            self.client.table("profiles")
            .select("telegram_user_id,preferred_language")
            .eq("id", profile_id)
            .limit(1)
        )
        if not result.data:
            raise DatabaseError("Request owner profile was not found")
        profile = result.data[0]
        if profile.get("telegram_user_id") is None:
            raise DatabaseError("Request owner has no Telegram user ID")
        return profile

    async def get_request(self, kind: str, public_id: str) -> dict[str, Any]:
        if kind not in {"appointment", "support"}:
            raise ValueError("Unsupported request type")
        table = "appointments" if kind == "appointment" else "support_requests"
        result = await self._execute(
            self.client.table(table).select("*").eq("public_id", public_id).limit(1)
        )
        if not result.data:
            raise DatabaseError("Request was not found")
        return result.data[0]

    async def confirm_appointment(
        self, public_id: str, details: dict[str, str | None], admin_telegram_id: int
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        payload = {
            "status": "confirmed",
            "confirmed_date": details["confirmed_date"],
            "confirmed_time": details["confirmed_time"],
            "confirmed_service": details["confirmed_service"],
            "confirmed_doctor": details["confirmed_doctor"],
            "confirmation_comment": details.get("confirmation_comment"),
            "confirmed_start_at": details["confirmed_start_at"],
            "confirmed_at": now,
            "reminder_24h_sent_at": None,
            "client_confirmation_status": "pending",
            "assigned_admin_telegram_id": admin_telegram_id,
            "updated_at": now,
        }
        result = await self._execute(
            self.client.table("appointments").update(payload).eq("public_id", public_id).select("*")
        )
        if not result.data:
            raise DatabaseError("Appointment was not found")
        logger.info("Appointment confirmed: %s", public_id)
        return result.data[0]

    async def list_due_reminders(self, now_iso: str, cutoff_iso: str) -> list[dict[str, Any]]:
        result = await self._execute(
            self.client.table("appointments").select("*")
            .eq("status", "confirmed").is_("reminder_24h_sent_at", "null")
            .gt("confirmed_start_at", now_iso).lte("confirmed_start_at", cutoff_iso)
        )
        return result.data or []

    async def mark_reminder_sent(self, public_id: str) -> None:
        await self._execute(self.client.table("appointments").update({
            "reminder_24h_sent_at": datetime.now(UTC).isoformat(),
        }).eq("public_id", public_id))

    async def set_visit_response(self, public_id: str, action: str) -> dict[str, Any]:
        if action not in {"confirmed", "reschedule_requested", "cancelled"}:
            raise ValueError("Unsupported visit response")
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"client_confirmation_status": action, "updated_at": now}
        if action == "reschedule_requested":
            payload.update({"status": "in_progress", "reschedule_requested_at": now})
        elif action == "cancelled":
            payload.update({"status": "cancelled", "closed_at": now})
        result = await self._execute(
            self.client.table("appointments").update(payload).eq("public_id", public_id).select("*")
        )
        if not result.data:
            raise DatabaseError("Appointment was not found")
        return result.data[0]

    async def save_reschedule_request(self, public_id: str, requested: str) -> dict[str, Any]:
        record = await self.set_visit_response(public_id, "reschedule_requested")
        record["reschedule_request"] = requested
        return record

    async def list_appointments_between(self, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        result = await self._execute(
            self.client.table("appointments").select("*")
            .gte("confirmed_start_at", start_iso).lte("confirmed_start_at", end_iso)
            .order("confirmed_start_at")
        )
        return result.data or []

    async def list_new_requests(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for table, kind in (("appointments", "appointment"), ("support_requests", "support")):
            result = await self._execute(
                self.client.table(table).select("*").eq("status", "new").order("created_at")
            )
            rows.extend({**row, "kind": kind} for row in (result.data or []))
        return rows

    async def save_rating(self, public_id: str, rating: int) -> dict[str, Any]:
        if rating not in range(1, 6):
            raise ValueError("Rating must be between 1 and 5")
        result = await self._execute(
            self.client.table("appointments").update({
                "rating": rating, "reviewed_at": datetime.now(UTC).isoformat()
            }).eq("public_id", public_id).select("*")
        )
        if not result.data:
            raise DatabaseError("Appointment was not found")
        return result.data[0]

    async def save_review(self, public_id: str, review: str) -> None:
        await self._execute(self.client.table("appointments").update({
            "review": review[:2000], "reviewed_at": datetime.now(UTC).isoformat()
        }).eq("public_id", public_id))

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
