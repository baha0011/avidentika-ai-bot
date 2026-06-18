from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.handlers.admin import is_authorized_admin
from app.services.notification_service import admin_actions_keyboard, telegram_account_html
from app.utils.datetime_utils import utc_day_bounds
from app.utils.security import safe_html

logger = logging.getLogger(__name__)

ADMIN_PANEL_BUTTON = "⚙️ Админ-панель"


def admin_persistent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ADMIN_PANEL_BUTTON)]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Панель администратора",
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Новые заявки", callback_data="admin:list:new")],
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="admin:list:today"),
            InlineKeyboardButton("📆 Завтра", callback_data="admin:list:tomorrow"),
        ],
    ])


async def activate_persistent_panel(application) -> None:
    """Show the persistent admin keyboard without blocking bot startup on failure."""
    try:
        await application.bot.send_message(
            chat_id=application.bot_data["settings"].admin_chat_id,
            text="Панель администратора активна.",
            reply_markup=admin_persistent_keyboard(),
        )
    except Exception as exc:
        logger.warning("Could not activate persistent admin panel: %s", type(exc).__name__)


async def _check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if await is_authorized_admin(update, context):
        return True
    await update.effective_message.reply_text("Недостаточно прав.")
    return False


def _profile(record: dict) -> dict | None:
    profile = record.get("profiles")
    if isinstance(profile, list):
        return profile[0] if profile else None
    return profile if isinstance(profile, dict) else None


def _request_card(record: dict) -> str:
    service = (
        record.get("confirmed_service")
        or record.get("service")
        or "Обращение к администратору"
    )
    date = record.get("confirmed_date") or record.get("preferred_date") or "дата не указана"
    time = record.get("confirmed_time") or record.get("preferred_time") or "время не указано"
    doctor = record.get("confirmed_doctor") or "не назначен"
    return "\n".join([
        f"🔹 Номер заявки: <code>{safe_html(record['public_id'])}</code>",
        f"Имя: {safe_html(record.get('patient_name') or '—')}",
        f"Телефон: <code>{safe_html(record.get('phone') or '—')}</code>",
        f"Telegram: {telegram_account_html(_profile(record))}",
        f"Услуга: {safe_html(service)}",
        f"Дата записи: {safe_html(date)}",
        f"Время записи: {safe_html(time)}",
        f"Доктор: {safe_html(doctor)}",
    ])


async def day_list(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int) -> None:
    if not await _check(update, context): return
    day = datetime.now(ZoneInfo("Europe/Kyiv")) + timedelta(days=offset)
    start, end = utc_day_bounds(day)
    rows = await context.application.bot_data["db"].list_appointments_between(start, end)
    title = "сегодня" if offset == 0 else "завтра"
    text = f"📅 Записи на {title} ({day:%d.%m.%Y}):\n\n" + ("\n\n".join(_request_card(row) for row in rows) if rows else "Записей нет.")
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=admin_panel_keyboard()
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await day_list(update, context, 0)


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await day_list(update, context, 1)


async def new_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check(update, context): return
    rows = await context.application.bot_data["db"].list_new_requests()
    text = "🆕 Новые заявки:\n\n" + (
        "\n\n".join(_request_card(row) for row in rows[:30])
        if rows else "Новых заявок нет."
    )
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=admin_panel_keyboard()
    )


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check(update, context):
        return
    await update.effective_message.reply_text(
        "⚙️ Панель администратора",
        reply_markup=admin_panel_keyboard(),
    )


async def panel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.rsplit(":", 1)[-1]
    if action == "new":
        await new_requests(update, context)
    elif action == "today":
        await day_list(update, context, 0)
    elif action == "tomorrow":
        await day_list(update, context, 1)


async def find_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Использование: /find A-1234ABCD")
        return
    public_id = context.args[0].upper()
    kind = "appointment" if public_id.startswith("A-") else "support"
    try:
        row = await context.application.bot_data["db"].get_request(kind, public_id)
    except Exception:
        await update.effective_message.reply_text("Заявка не найдена.")
        return
    text = (
        f"<b>{safe_html(public_id)}</b>\nСтатус: {safe_html(row.get('status'))}\n"
        f"Клиент: {safe_html(row.get('patient_name'))}\nТелефон: {safe_html(row.get('phone'))}\n"
        f"Telegram: {telegram_account_html(_profile(row))}\n"
        f"Услуга: {safe_html(row.get('confirmed_service') or row.get('service') or '—')}\n"
        f"Дата записи: {safe_html(row.get('confirmed_date') or row.get('preferred_date') or '—')}\n"
        f"Время записи: {safe_html(row.get('confirmed_time') or row.get('preferred_time') or '—')}\n"
        f"Доктор: {safe_html(row.get('confirmed_doctor') or 'не назначен')}"
    )
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=admin_actions_keyboard(kind, public_id, row["status"])
    )
