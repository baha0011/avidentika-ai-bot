from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.utils.security import safe_html


async def change_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    settings = context.application.bot_data["settings"]
    if update.effective_chat.id != settings.admin_chat_id:
        await query.answer("Недостаточно прав", show_alert=True)
        return
    # In a private admin chat only its owner is allowed. In a group, require
    # Telegram administrator/owner status, not merely group membership.
    if getattr(update.effective_chat, "type", "private") == "private":
        authorized = update.effective_user.id == settings.admin_chat_id
    else:
        try:
            member = await context.bot.get_chat_member(settings.admin_chat_id, update.effective_user.id)
            authorized = member.status in {"administrator", "creator", "owner"}
        except Exception:
            authorized = False
    if not authorized:
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
    actor = safe_html(update.effective_user.full_name)
    changed = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")
    original = query.message.text_html or safe_html(query.message.text)
    # Replace the final status line without altering submitted personal data.
    lines = [line for line in original.splitlines() if not line.startswith("Статус:") and not line.startswith("Изменил:")]
    lines.extend([f"Статус: <b>{safe_html(record['status'])}</b>", f"Изменил: {actor}, {changed} (Киев)"])
    keyboard = None
    if status == "in_progress":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Закрыть заявку", callback_data=f"adm:{kind}:{public_id}:closed")
        ]])
    await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
