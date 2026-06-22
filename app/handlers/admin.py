from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from app.utils.security import safe_html
from app.services.notification_service import admin_actions_keyboard, client_status_text
from app.services.web_notification_store import WebNotificationStore

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


async def _deliver_status_notice(context: ContextTypes.DEFAULT_TYPE, kind: str, record: dict) -> tuple[bool, str]:
    db = context.application.bot_data["db"]
    store = WebNotificationStore(db)
    target = await store.get_profile_delivery_target(record["user_id"])
    text = client_status_text(record, target)
    delivered_to: list[str] = []

    if target.get("telegram_user_id") is not None:
        try:
            await context.application.bot_data["notifications"].notify_client_status(context.bot, record, target)
            delivered_to.append("Telegram")
        except Exception as exc:
            logger.warning("Telegram status notification failed for %s: %s", record.get("public_id"), type(exc).__name__)

    if target.get("web_session_id"):
        try:
            await store.create_notification(
                target["web_session_id"],
                record["public_id"],
                kind,
                "status",
                text,
            )
            delivered_to.append("website chat")
        except Exception as exc:
            logger.warning("Website status notification failed for %s: %s", record.get("public_id"), type(exc).__name__)

    return bool(delivered_to), ", ".join(delivered_to)


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

    delivered = False
    delivery_target = ""
    try:
        delivered, delivery_target = await _deliver_status_notice(context, kind, record)
        if kind == "appointment" and status == "closed":
            profile = await context.application.bot_data["db"].get_profile_notification_target(record["user_id"])
            await context.application.bot_data["notifications"].request_rating(context.bot, record, profile)
    except Exception as exc:
        logger.warning(
            "Client status notification failed for request %s: %s",
            public_id,
            type(exc).__name__,
        )

    actor = safe_html(update.effective_user.full_name)
    changed = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")
    original = query.message.text_html or safe_html(query.message.text)
    lines = [line for line in original.splitlines() if not line.startswith("Статус:") and not line.startswith("Изменил:") and not line.startswith("Доставка:")]
    lines.extend([f"Статус: <b>{safe_html(record['status'])}</b>", f"Изменил: {actor}, {changed} (Киев)"])
    lines.append(f"Доставка: {'✅ ' + safe_html(delivery_target) if delivered else '⚠️ клиенту не доставлено'}")
    keyboard = admin_actions_keyboard(kind, public_id, status)
    await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
