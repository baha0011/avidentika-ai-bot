from app.handlers.admin_commands import (
    ADMIN_PANEL_BUTTON,
    _request_card,
    admin_panel_keyboard,
    admin_persistent_keyboard,
)


def test_admin_panel_has_request_and_schedule_buttons() -> None:
    keyboard = admin_panel_keyboard().inline_keyboard
    buttons = [button for row in keyboard for button in row]

    assert [(button.text, button.callback_data) for button in buttons] == [
        ("🆕 Новые заявки", "admin:list:new"),
        ("📅 Сегодня", "admin:list:today"),
        ("📆 Завтра", "admin:list:tomorrow"),
    ]


def test_admin_panel_has_persistent_launcher_button() -> None:
    keyboard = admin_persistent_keyboard()

    assert keyboard.is_persistent is True
    assert keyboard.keyboard[0][0].text == ADMIN_PANEL_BUTTON


def test_request_card_contains_required_client_details() -> None:
    text = _request_card({
        "public_id": "A-1234ABCD",
        "patient_name": "Олена",
        "phone": "+380671234567",
        "service": "Діагностика",
        "preferred_date": "25.06.2026",
        "preferred_time": "15:30",
        "confirmed_doctor": "Амін",
        "profiles": {"username": "olena_test", "telegram_user_id": 321},
    })

    assert "Номер заявки: <code>A-1234ABCD</code>" in text
    assert "Имя: Олена" in text
    assert "Телефон: <code>+380671234567</code>" in text
    assert "Telegram: @olena_test" in text
    assert "Услуга: Діагностика" in text
    assert "Дата записи: 25.06.2026" in text
    assert "Время записи: 15:30" in text
    assert "Доктор: Амін" in text
