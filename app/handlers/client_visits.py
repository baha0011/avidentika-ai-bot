from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

logger = logging.getLogger(__name__)
RESCHEDULE_TEXT, REVIEW_TEXT = 300, 301


async def _owned_record(update: Update, context: ContextTypes.DEFAULT_TYPE, public_id: str):
    db = context.application.bot_data["db"]
    record = await db.get_request("appointment", public_id)
    profile = await db.get_profile_notification_target(record["user_id"])
    if int(profile["telegram_user_id"]) != update.effective_user.id:
        raise PermissionError
    return record, profile


async def visit_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, public_id, action = query.data.split(":", 2)
    try:
        _, profile = await _owned_record(update, context, public_id)
        db_action = "confirmed" if action == "confirm" else "cancelled"
        record = await context.application.bot_data["db"].set_visit_response(public_id, db_action)
    except Exception:
        await query.answer("Не удалось изменить визит", show_alert=True)
        return
    await query.answer()
    lang = profile.get("preferred_language")
    if lang == "ru":
        text = "✅ Визит подтверждён." if action == "confirm" else "❌ Визит отменён. Администратор уведомлён."
    else:
        text = "✅ Візит підтверджено." if action == "confirm" else "❌ Візит скасовано. Адміністратор повідомлений."
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(text)
    event = "Клиент подтвердил визит." if action == "confirm" else "Клиент отменил визит."
    await context.application.bot_data["notifications"].notify_admin_event(context.bot, record, event)


async def begin_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, public_id, _ = query.data.split(":", 2)
    try:
        _, profile = await _owned_record(update, context, public_id)
    except Exception:
        await query.answer("Недостаточно прав", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    lang = profile.get("preferred_language") if profile.get("preferred_language") in {"uk", "ru"} else "uk"
    context.user_data["visit_flow"] = {"public_id": public_id, "language": lang}
    await query.message.reply_text(
        "Напишіть бажані нові дату й час та, за потреби, коментар.\nНаприклад: 27.06 після 16:00"
        if lang == "uk" else
        "Напишите желаемые новые дату и время и, при необходимости, комментарий.\nНапример: 27.06 после 16:00"
    )
    return RESCHEDULE_TEXT


async def save_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    public_id = context.user_data["visit_flow"]["public_id"]
    requested = update.effective_message.text.strip()[:500]
    record = await context.application.bot_data["db"].save_reschedule_request(public_id, requested)
    await context.application.bot_data["notifications"].notify_admin_event(
        context.bot, record, f"Клиент просит перенести визит:\n{requested}"
    )
    lang = context.user_data["visit_flow"].get("language")
    await update.effective_message.reply_text(
        "✅ Запит на перенесення передано адміністратору. З вами зв'яжуться."
        if lang == "uk" else "✅ Запрос на перенос передан администратору. С вами свяжутся."
    )
    context.user_data.pop("visit_flow", None)
    return ConversationHandler.END


async def begin_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, public_id, value = query.data.split(":", 2)
    try:
        _, profile = await _owned_record(update, context, public_id)
        record = await context.application.bot_data["db"].save_rating(public_id, int(value))
    except Exception:
        await query.answer("Не удалось сохранить оценку", show_alert=True)
        return ConversationHandler.END
    await query.answer("Спасибо!")
    await query.edit_message_reply_markup(reply_markup=None)
    lang = profile.get("preferred_language") if profile.get("preferred_language") in {"uk", "ru"} else "uk"
    context.user_data["review_flow"] = {"public_id": public_id, "language": lang}
    await query.message.reply_text(
        "Дякуємо за оцінку! Напишіть короткий відгук або надішліть /skip."
        if lang == "uk" else "Спасибо за оценку! Напишите короткий отзыв или отправьте /skip."
    )
    await context.application.bot_data["notifications"].notify_admin_event(
        context.bot, record, f"Клиент поставил оценку: {value}/5"
    )
    return REVIEW_TEXT


async def save_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    public_id = context.user_data["review_flow"]["public_id"]
    review = update.effective_message.text.strip()
    await context.application.bot_data["db"].save_review(public_id, review)
    record = await context.application.bot_data["db"].get_request("appointment", public_id)
    await context.application.bot_data["notifications"].notify_admin_event(context.bot, record, f"Новый отзыв:\n{review[:1000]}")
    lang = context.user_data["review_flow"].get("language")
    await update.effective_message.reply_text("✅ Дякуємо за ваш відгук!" if lang == "uk" else "✅ Спасибо за ваш отзыв!")
    context.user_data.pop("review_flow", None)
    return ConversationHandler.END


async def skip_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("review_flow", None)
    await update.effective_message.reply_text("Дякуємо за оцінку!")
    return ConversationHandler.END


def conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(begin_reschedule, pattern=r"^visit:A-[A-F0-9]{8}:reschedule$"),
            CallbackQueryHandler(begin_rating, pattern=r"^rate:A-[A-F0-9]{8}:[1-5]$"),
        ],
        states={
            RESCHEDULE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reschedule)],
            REVIEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_review)],
        },
        fallbacks=[CommandHandler("skip", skip_review)],
        allow_reentry=True,
    )
