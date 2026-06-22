from __future__ import annotations

from typing import Any


class WebNotificationStore:
    table_name = "web_messages"

    def __init__(self, db: Any) -> None:
        self.db = db

    async def get_profile_delivery_target(self, profile_id: str) -> dict[str, Any]:
        result = await self.db._execute(
            self.db.client.table("profiles")
            .select("telegram_user_id,preferred_language,web_session_id,username")
            .eq("id", profile_id)
            .limit(1)
        )
        if not result.data:
            raise RuntimeError("Request owner profile was not found")
        return result.data[0]

    async def create_notification(
        self,
        web_session_id: str,
        public_id: str,
        kind: str,
        event_type: str,
        message: str,
    ) -> dict[str, Any]:
        payload = {
            "web_session_id": web_session_id,
            "public_id": public_id,
            "kind": kind,
            "event_type": event_type,
            "message": message[:2000],
        }
        result = await self.db._execute(
            self.db.client.table(self.table_name).insert(payload).select("id")
        )
        if not result.data:
            raise RuntimeError("Web notification was not created")
        return result.data[0]

    async def list_notifications(self, web_session_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        query = self.db.client.table(self.table_name).select(
            "id,public_id,kind,event_type,message,created_at"
        ).eq("web_session_id", web_session_id)
        if after_id > 0:
            query = query.gt("id", after_id)
        result = await self.db._execute(query.order("id").limit(30))
        return result.data or []
