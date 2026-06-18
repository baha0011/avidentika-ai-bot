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


def source_keyboard(lang: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Джерело на сайті" if lang == "uk" else "Источник на сайте", url=url)]])


REMOVE_KEYBOARD = ReplyKeyboardRemove()
