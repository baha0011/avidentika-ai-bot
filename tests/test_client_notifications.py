import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.notification_service import NotificationService


def _sent_text(status: str, language: str) -> str:
    bot = SimpleNamespace(send_message=AsyncMock())
    record = {"public_id": "A-1234ABCD", "status": status}
    profile = {"telegram_user_id": 321, "preferred_language": language}
    asyncio.run(NotificationService(999).notify_client_status(bot, record, profile))
    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.kwargs["chat_id"] == 321
    return bot.send_message.await_args.kwargs["text"]


def test_client_notification_in_progress() -> None:
    assert _sent_text("in_progress", "ru") == (
        "✅ Администратор взял вашу заявку A-1234ABCD в работу. Скоро с вами свяжутся."
    )


def test_client_notification_closed() -> None:
    assert _sent_text("closed", "uk") == (
        "✅ Вашу заявку A-1234ABCD закрито адміністратором."
    )


def test_client_notification_cancelled() -> None:
    assert _sent_text("cancelled", "uk") == (
        "❌ Вашу заявку A-1234ABCD відхилено. Для уточнення натисніть “Зв'язатися з адміністратором” "
        "або зателефонуйте +38 066 200 05 23."
    )


def test_admin_free_text_message_reaches_client() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    record = {"public_id": "A-1234ABCD"}
    profile = {"telegram_user_id": 321, "preferred_language": "ru"}
    asyncio.run(NotificationService(999).notify_client_message(bot, record, profile, "Возьмите паспорт."))
    assert bot.send_message.await_args.kwargs["chat_id"] == 321
    assert bot.send_message.await_args.kwargs["text"] == (
        "💬 Сообщение от администратора AVIDENTIKA по заявке A-1234ABCD:\n\nВозьмите паспорт."
    )


def test_structured_appointment_confirmation_reaches_client() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    record = {
        "public_id": "A-1234ABCD",
        "confirmed_date": "25.06.2026",
        "confirmed_time": "15:30",
        "confirmed_service": "Лікування каналів",
        "confirmed_doctor": "Амін",
        "confirmation_comment": None,
    }
    profile = {"telegram_user_id": 321, "preferred_language": "uk"}
    asyncio.run(NotificationService(999).notify_appointment_confirmation(bot, record, profile))
    text = bot.send_message.await_args.kwargs["text"]
    assert "Ваш запис A-1234ABCD підтверджено" in text
    assert "📅 Дата: 25.06.2026" in text
    assert "👨‍⚕️ Лікар: Амін" in text


def test_24h_reminder_has_visit_actions() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    record = {
        "public_id": "A-1234ABCD", "confirmed_date": "25.06.2026", "confirmed_time": "15:30",
        "confirmed_service": "Лікування", "confirmed_doctor": "Амін",
    }
    asyncio.run(NotificationService(999).send_visit_reminder(
        bot, record, {"telegram_user_id": 321, "preferred_language": "uk"}
    ))
    keyboard = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
    callbacks = [row[0].callback_data for row in keyboard]
    assert callbacks == [
        "visit:A-1234ABCD:confirm", "visit:A-1234ABCD:reschedule", "visit:A-1234ABCD:cancel"
    ]


def test_rating_request_has_five_buttons() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    asyncio.run(NotificationService(999).request_rating(
        bot, {"public_id": "A-1234ABCD"}, {"telegram_user_id": 321, "preferred_language": "ru"}
    ))
    keyboard = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
    assert len(keyboard[0]) == 5
