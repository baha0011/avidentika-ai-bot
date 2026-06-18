from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.keyboards import main_menu
from app.utils.language import detect_language


def user_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    stored = context.user_data.get("language")
    if stored in {"uk", "ru"}:
        return stored
    text = update.effective_message.text if update.effective_message else ""
    language = detect_language(text or "")
    context.user_data["language"] = language
    return language


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = user_language(update, context)
    text = (
        "Вітаємо у стоматологічній клініці AVIDENTIKA. Я — віртуальний асистент. "
        "Допоможу дізнатися про послуги й ціни, знайти контакти або залишити попередню заявку на прийом."
        if lang == "uk" else
        "Добро пожаловать в стоматологическую клинику AVIDENTIKA. Я — виртуальный ассистент. "
        "Помогу узнать об услугах и ценах, найти контакты или оставить предварительную заявку на приём."
    )
    await update.effective_message.reply_text(text, reply_markup=main_menu(lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = user_language(update, context)
    text = (
        "Напишіть запитання звичайним повідомленням або скористайтеся меню. /cancel — скасувати заповнення, /privacy — конфіденційність."
        if lang == "uk" else
        "Напишите вопрос обычным сообщением или воспользуйтесь меню. /cancel — отменить заполнение, /privacy — конфиденциальность."
    )
    await update.effective_message.reply_text(text, reply_markup=main_menu(lang))


async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = user_language(update, context)
    text = (
        "🔐 Це демонстраційна система. Для заявки бот збирає ім'я, телефон і надані вами деталі, щоб передати їх адміністратору клініки. "
        "Ви можете не надсилати персональні дані й скасувати сценарій. AI може помилятися та не замінює лікаря. "
        "Дата й час стають остаточними лише після підтвердження адміністратором."
        if lang == "uk" else
        "🔐 Это демонстрационная система. Для заявки бот собирает имя, телефон и предоставленные вами детали, чтобы передать их администратору клиники. "
        "Вы можете не отправлять персональные данные и отменить сценарий. AI может ошибаться и не заменяет врача. "
        "Дата и время становятся окончательными только после подтверждения администратором."
    )
    await update.effective_message.reply_text(text, reply_markup=main_menu(lang))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = user_language(update, context)
    context.user_data.pop("appointment", None)
    context.user_data.pop("support", None)
    await update.effective_message.reply_text(
        "Заповнення скасовано." if lang == "uk" else "Заполнение отменено.",
        reply_markup=main_menu(lang),
    )
    return -1


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = user_language(update, context)
    await query.message.reply_text(
        "Головне меню:" if lang == "uk" else "Главное меню:",
        reply_markup=main_menu(lang),
    )
