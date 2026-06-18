from app.handlers.admin_commands import (
    ADMIN_PANEL_BUTTON,
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
