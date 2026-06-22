from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.handlers.admin import is_authorized_admin
from app.services.notification_service import (
    admin_actions_keyboard,
    appointment_confirmation_text,
    client_admin_message_text,
)
from app.services.web_notification_store import WebNotificationStore
from app.utils.security import safe_html
from app.utils.datetime_utils import parse_appointment_datetime

logger = logging.getLogger(__name__)

REPLY_TEXT, CONFIRM_DATE, CONFIRM_TIME, CONFIRM_SERVICE, CONFIRM_DOCTOR, CONFIRM_COMMENT, CONFIRM_FINAL = range(100, 107)


async def _authorized_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if await is_authorized_admin(update, context):
        return True
    await update.callback_query.answer("Недостаточно прав", show_alert=True)
    return False


async def _deliver_client_text(
    context: ContextTypes.DEFAULT_TYPE,
    record: dict,
    kind: str,
    event_type: str,
    text: str,
    telegram_sender,
) -> tuple[bool, str]:
    db = context.application.bot_data["db"]
    store = WebNotificationStore(db)
    target = await store.get_profile_delivery_target(record["user_id"])
    delivered_to: list[str] = []

    if target.get("telegram_user_id") is not None:
        try:
            await telegram_sender(target)
            delivered_to.append("Telegram")
        except Exception as exc:
            logger.warning("Telegram delivery failed for %s: %s", record.get("public_id"), type(exc).__name__)

    if target.get("web_session_id"):
        try:
            await store.create_notification(
                target["web_session_id"],
                record["public_id"],
                kind,
                event_type,
                text,
            )
            delivered_to.append("website chat")
        except Exception as exc:
            logger.warning("Website delivery failed for %s: %s", record.get("public_id"), type(exc).__name__)

    return bool(delivered_to), ", ".join(delivered_to)


async def begin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _authorized_callback(update, context):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    _, kind, public_id = query.data.split(":", 2)
    context.user_data["admin_flow"] = {"kind": kind, "public_id": public_id}
    await query.message.reply_text(
        f"Введите сообщение для клиента по заявке {public_id}.\n\n/cancel — отменить."
    )
    return REPLY_TEXT


async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    flow = context.user_data.get("admin_flow", {})
    text = (update.effective_message.text or "").strip()
    if not text or len(text) > 2000:
        await update.effective_message.reply_text("Сообщение должно содержать от 1 до 2000 символов.")
        return REPLY_TEXT
    try:
        db = context.application.bot_data["db"]
        record = await db.get_request(flow["kind"], flow["public_id"])
        store = WebNotificationStore(db)
        target = await store.get_profile_delivery_target(record["user_id"])
        outbound_text = client_admin_message_text(record, target, text)
        delivered, target_name = await _deliver_client_text(
            context,
            record,
            flow["kind"],
            "admin_message",
            outbound_text,
            lambda profile: context.application.bot_data["notifications"].notify_client_message(
                context.bot, record, profile, text
            ),
        )
    except Exception as exc:
        logger.warning("Admin message delivery failed for %s: %s", flow.get("public_id"), type(exc).__name__)
        await update.effective_message.reply_text("⚠️ Не удалось доставить сообщение клиенту.")
    else:
        await update.effective_message.reply_text(
            f"✅ Сообщение отправлено клиенту: {target_name}." if delivered else "⚠️ Сообщение сохранено, но клиенту не доставлено."
        )
    context.user_data.pop("admin_flow", None)
    return ConversationHandler.END


async def begin_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _authorized_callback(update, context):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    _, _, public_id = query.data.split(":", 2)
    context.user_data["admin_flow"] = {
        "kind": "appointment",
        "public_id": public_id,
        "source_chat_id": query.message.chat_id,
        "source_message_id": query.message.message_id,
        "source_text_html": query.message.text_html or safe_html(query.message.text),
    }
    await query.message.reply_text(f"Подтверждение записи {public_id}.\nВведите дату, например: 25.06.2026\n\n/cancel — отменить.")
    return CONFIRM_DATE


async def collect_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    try:
        datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        await update.effective_message.reply_text("Неверная дата. Используйте формат 25.06.2026")
        return CONFIRM_DATE
    context.user_data["admin_flow"]["confirmed_date"] = value
    await update.effective_message.reply_text("Введите время, например: 15:30")
    return CONFIRM_TIME


async def collect_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    flow = context.user_data["admin_flow"]
    value = update.effective_message.text.strip()
    try:
        starts_at = parse_appointment_datetime(flow["confirmed_date"], value)
        if starts_at <= datetime.now(ZoneInfo("Europe/Kyiv")):
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text("Неверное время или дата уже прошла. Введите дату заново в формате 25.06.2026")
        return CONFIRM_DATE
    flow["confirmed_time"] = value[:80]
    flow["confirmed_start_at"] = starts_at.astimezone(ZoneInfo("UTC")).isoformat()
    await update.effective_message.reply_text("Введите процедуру или услугу:")
    return CONFIRM_SERVICE


async def collect_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["admin_flow"]["confirmed_service"] = update.effective_message.text.strip()[:200]
    await update.effective_message.reply_text("Введите имя врача:")
    return CONFIRM_DOCTOR


async def collect_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["admin_flow"]["confirmed_doctor"] = update.effective_message.text.strip()[:120]
    await update.effective_message.reply_text("Добавьте комментарий или отправьте «-», если комментария нет:")
    return CONFIRM_COMMENT


async def collect_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    flow = context.user_data["admin_flow"]
    value = update.effective_message.text.strip()
    flow["confirmation_comment"] = None if value == "-" else value[:500]
    summary = (
        f"<b>Подтвердить запись {safe_html(flow['public_id'])}?</b>\n"
        f"Дата: {safe_html(flow['confirmed_date'])}\n"
        f"Время: {safe_html(flow['confirmed_time'])}\n"
        f"Процедура: {safe_html(flow['confirmed_service'])}\n"
        f"Врач: {safe_html(flow['confirmed_doctor'])}\n"
        f"Комментарий: {safe_html(flow.get('confirmation_comment') or '—')}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Подтвердить и отправить", callback_data="bookconfirm:send"),
        InlineKeyboardButton("Отменить", callback_data="bookconfirm:cancel"),
    ]])
    await update.effective_message.reply_text(summary, parse_mode="HTML", reply_markup=keyboard)
    return CONFIRM_FINAL


async def finish_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "bookconfirm:cancel":
        context.user_data.pop("admin_flow", None)
        await query.edit_message_text("Подтверждение записи отменено.")
        return ConversationHandler.END
    flow = context.user_data["admin_flow"]
    db = context.application.bot_data["db"]
    details = {key: flow.get(key) for key in (
        "confirmed_date", "confirmed_time", "confirmed_service", "confirmed_doctor",
        "confirmation_comment", "confirmed_start_at"
    )}
    try:
        record = await db.confirm_appointment(flow["public_id"], details, update.effective_user.id)
    except Exception:
        logger.exception("Appointment confirmation database update failed")
        await query.edit_message_text("❌ Не удалось сохранить подтверждение записи.")
        return ConversationHandler.END

    delivered = False
    delivery_target = ""
    try:
        store = WebNotificationStore(db)
        target = await store.get_profile_delivery_target(record["user_id"])
        outbound_text = appointment_confirmation_text(record, target)
        delivered, delivery_target = await _deliver_client_text(
            context,
            record,
            "appointment",
            "confirmation",
            outbound_text,
            lambda profile: context.application.bot_data["notifications"].notify_appointment_confirmation(
                context.bot, record, profile
            ),
        )
    except Exception as exc:
        logger.warning("Confirmation delivery failed for %s: %s", flow["public_id"], type(exc).__name__)

    actor = safe_html(update.effective_user.full_name)
    changed = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")
    lines = [line for line in flow["source_text_html"].splitlines()
             if not line.startswith("Статус:") and not line.startswith("Изменил:") and not line.startswith("Доставка:")]
    lines.extend([
        f"Подтверждено: {safe_html(record['confirmed_date'])}, {safe_html(record['confirmed_time'])}",
        f"Врач: {safe_html(record['confirmed_doctor'])}",
        "Статус: <b>confirmed</b>",
        f"Изменил: {actor}, {changed} (Киев)",
        f"Доставка: {'✅ ' + safe_html(delivery_target) if delivered else '⚠️ клиенту не доставлено'}",
    ])
    try:
        await context.bot.edit_message_text(
            chat_id=flow["source_chat_id"], message_id=flow["source_message_id"],
            text="\n".join(lines), parse_mode="HTML",
            reply_markup=admin_actions_keyboard("appointment", flow["public_id"], "confirmed"),
        )
    except Exception:
        logger.warning("Could not update original admin appointment message: %s", flow["public_id"])
    await query.edit_message_text(
        f"✅ Запись подтверждена, клиент уведомлён: {delivery_target}."
        if delivered else
        "⚠️ Статус confirmed сохранён, но сообщение клиенту не доставлено."
    )
    context.user_data.pop("admin_flow", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("admin_flow", None)
    await update.effective_message.reply_text("Действие администратора отменено.")
    return ConversationHandler.END


def conversation() -> ConversationHandler:
    text = MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply)
    collect = lambda fn: MessageHandler(filters.TEXT & ~filters.COMMAND, fn)
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(begin_reply, pattern=r"^admreply:(appointment|support):[AS]-[A-F0-9]{8}$"),
            CallbackQueryHandler(begin_confirmation, pattern=r"^admconfirm:appointment:A-[A-F0-9]{8}$"),
        ],
        states={
            REPLY_TEXT: [text],
            CONFIRM_DATE: [collect(collect_date)],
            CONFIRM_TIME: [collect(collect_time)],
            CONFIRM_SERVICE: [collect(collect_service)],
            CONFIRM_DOCTOR: [collect(collect_doctor)],
            CONFIRM_COMMENT: [collect(collect_comment)],
            CONFIRM_FINAL: [CallbackQueryHandler(finish_confirmation, pattern=r"^bookconfirm:(send|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
