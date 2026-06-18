import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.handlers.admin import change_status
from app.models.schemas import AppointmentInput


def test_appointment_record_has_new_status() -> None:
    record = AppointmentInput("Олена", "+380671234567", "Ортодонтія").to_record("user-id")
    assert record["status"] == "new"
    assert record["user_id"] == "user-id"


def test_outsider_cannot_manage_request() -> None:
    query = SimpleNamespace(answer=AsyncMock(), data="adm:appointment:A-1234ABCD:closed")
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=111),
    )
    db = SimpleNamespace(update_request_status=AsyncMock())
    context = SimpleNamespace(application=SimpleNamespace(bot_data={"settings": SimpleNamespace(admin_chat_id=999), "db": db}))
    asyncio.run(change_status(update, context))
    query.answer.assert_awaited_once()
    db.update_request_status.assert_not_awaited()
