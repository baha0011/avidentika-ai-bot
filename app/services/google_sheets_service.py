from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Optional webhook adapter for mirroring requests and history to Google Sheets."""

    def __init__(
        self,
        enabled: bool = False,
        web_app_url: str = "",
        webhook_secret: str = "",
        *,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.enabled = bool(enabled and web_app_url)
        self.web_app_url = web_app_url
        self.webhook_secret = webhook_secret
        self.timeout_seconds = timeout_seconds

    async def _post(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        if self.webhook_secret:
            payload = {**payload, "webhook_secret": self.webhook_secret}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.web_app_url, json=payload)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Google Sheets sync failed: %s", type(exc).__name__)

    async def sync_appointment(self, record: dict[str, Any], event: str, details: str = "") -> None:
        await self._post({"type": "appointment", "event": event, "details": details, "record": record})

    async def append_history(self, record: dict[str, Any], event: str, details: str = "") -> None:
        await self._post({"type": "history", "event": event, "details": details, "record": record})
