import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.handlers.admin import change_status
from app.models.schemas import AppointmentInput
from app.services.notification_service import NotificationService


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


def test_status_is_saved_when_client_notification_fails() -> None:
    record = {
        "public_id": "A-1234ABCD",
        "user_id": "profile-id",
        "status": "in_progress",
    }
    db = SimpleNamespace(
        update_request_status=AsyncMock(return_value=record),
        get_profile_notification_target=AsyncMock(return_value={
            "telegram_user_id": 321,
            "preferred_language": "ru",
        }),
    )
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError("bot blocked")))
    query = SimpleNamespace(
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        data="adm:appointment:A-1234ABCD:in_progress",
        message=SimpleNamespace(
            text_html="<b>Новая заявка</b>\nСтатус: <b>new</b>",
            text="Новая заявка\nСтатус: new",
        ),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=999, type="private"),
        effective_user=SimpleNamespace(id=999, full_name="Admin"),
    )
    context = SimpleNamespace(
        bot=bot,
        application=SimpleNamespace(bot_data={
            "settings": SimpleNamespace(admin_chat_id=999),
            "db": db,
            "notifications": NotificationService(999),
        }),
    )

    asyncio.run(change_status(update, context))

    db.update_request_status.assert_awaited_once_with("appointment", "A-1234ABCD", "in_progress", 999)
    db.get_profile_notification_target.assert_awaited_once_with("profile-id")
    bot.send_message.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()
