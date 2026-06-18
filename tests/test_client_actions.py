from app.keyboards.keyboards import client_actions_keyboard, client_main_menu_keyboard


def test_russian_client_actions() -> None:
    keyboard = client_actions_keyboard("ru").inline_keyboard
    assert keyboard[0][0].callback_data == "quick:book"
    assert keyboard[0][0].text == "🦷 Записаться на приём"
    assert keyboard[1][0].callback_data == "quick:ask"
    assert keyboard[2][0].callback_data == "quick:support"


def test_ukrainian_client_actions() -> None:
    keyboard = client_actions_keyboard("uk").inline_keyboard
    assert keyboard[0][0].text == "🦷 Записатися на прийом"
    assert keyboard[1][0].text == "❓ Поставити запитання"
    assert keyboard[2][0].text == "💬 Зв'язатися з адміністратором"


def test_status_notification_has_main_menu_button() -> None:
    keyboard = client_main_menu_keyboard("uk").inline_keyboard
    assert keyboard[0][0].text == "🏠 Головне меню"
    assert keyboard[0][0].callback_data == "quick:menu"
