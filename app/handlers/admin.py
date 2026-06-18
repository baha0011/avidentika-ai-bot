from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from app.utils.security import safe_html
from app.services.notification_service import admin_actions_keyboard

logger = logging.getLogger(__name__)


async def is_authorized_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = context.application.bot_data["settings"]
    if update.effective_chat.id != settings.admin_chat_id:
        return False
    if getattr(update.effective_chat, "type", "private") == "private":
        return update.effective_user.id == settings.admin_chat_id
    try:
        member = await context.bot.get_chat_member(settings.admin_chat_id, update.effective_user.id)
        return member.status in {"administrator", "creator", "owner"}
    except Exception:
        return False


async def change_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await is_authorized_admin(update, context):
        await query.answer("Недостаточно прав", show_alert=True)
        return
    try:
        _, kind, public_id, status = query.data.split(":", 3)
        record = await context.application.bot_data["db"].update_request_status(
            kind, public_id, status, update.effective_user.id
        )
    except Exception:
        await query.answer("Не удалось изменить статус", show_alert=True)
        return
    await query.answer("Статус обновлён")
    try:
        profile = await context.application.bot_data["db"].get_profile_notification_target(record["user_id"])
        await context.application.bot_data["notifications"].notify_client_status(context.bot, record, profile)
        if kind == "appointment" and status == "closed":
            await context.application.bot_data["notifications"].request_rating(context.bot, record, profile)
    except Exception as exc:
        # The database status is already committed. A blocked bot or other
        # Telegram delivery error must not roll it back or stop admin UI update.
        logger.warning(
            "Client status notification failed for request %s: %s",
            public_id,
            type(exc).__name__,
        )
    actor = safe_html(update.effective_user.full_name)
    changed = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")
    original = query.message.text_html or safe_html(query.message.text)
    # Replace the final status line without altering submitted personal data.
    lines = [line for line in original.splitlines() if not line.startswith("Статус:") and not line.startswith("Изменил:")]
    lines.extend([f"Статус: <b>{safe_html(record['status'])}</b>", f"Изменил: {actor}, {changed} (Киев)"])
    keyboard = admin_actions_keyboard(kind, public_id, status)
    await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
