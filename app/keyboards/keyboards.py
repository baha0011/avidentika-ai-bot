from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

TEXT = {
    "uk": {
        "ask": "Поставити запитання", "services": "Послуги та ціни", "book": "Записатися на прийом",
        "address": "Адреса та графік", "support": "Зв'язатися з адміністратором",
        "cancel": "Скасувати", "skip": "Пропустити", "confirm": "Підтвердити", "change": "Змінити",
    },
    "ru": {
        "ask": "Задать вопрос", "services": "Услуги и цены", "book": "Записаться на приём",
        "address": "Адрес и график", "support": "Связаться с администратором",
        "cancel": "Отменить", "skip": "Пропустить", "confirm": "Подтвердить", "change": "Изменить",
    },
}


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    t = TEXT[lang]
    return ReplyKeyboardMarkup(
        [[t["ask"], t["services"]], [t["book"]], [t["address"], t["support"]]],
        resize_keyboard=True,
    )


def cancel_keyboard(lang: str, *, contact: bool = False, skip: bool = False) -> ReplyKeyboardMarkup:
    rows = []
    if contact:
        rows.append([KeyboardButton("📱 Надіслати номер" if lang == "uk" else "📱 Отправить номер", request_contact=True)])
    if skip:
        rows.append([TEXT[lang]["skip"]])
    rows.append([TEXT[lang]["cancel"]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def confirmation_keyboard(lang: str, prefix: str) -> InlineKeyboardMarkup:
    t = TEXT[lang]
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t["confirm"], callback_data=f"{prefix}:confirm"),
        InlineKeyboardButton(t["change"], callback_data=f"{prefix}:change"),
        InlineKeyboardButton(t["cancel"], callback_data=f"{prefix}:cancel"),
    ]])


def client_actions_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🦷 Записатися на прийом" if lang == "uk" else "🦷 Записаться на приём",
            callback_data="quick:book",
        )],
        [InlineKeyboardButton(
            "❓ Поставити запитання" if lang == "uk" else "❓ Задать вопрос",
            callback_data="quick:ask",
        )],
        [InlineKeyboardButton(
            "💬 Зв'язатися з адміністратором" if lang == "uk" else "💬 Связаться с администратором",
            callback_data="quick:support",
        )],
    ])


def client_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🏠 Головне меню" if lang == "uk" else "🏠 Главное меню",
            callback_data="quick:menu",
        )
    ]])


REMOVE_KEYBOARD = ReplyKeyboardRemove()
