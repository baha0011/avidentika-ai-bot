from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.handlers.start import cancel, user_language
from app.keyboards.keyboards import TEXT, cancel_keyboard, confirmation_keyboard, main_menu
from app.models.schemas import AppointmentInput
from app.utils.phone import normalize_ua_phone
from app.utils.security import safe_html

NAME, PHONE, SERVICE, DATE, TIME, COMMENT, CONFIRM = range(7)


def _is_cancel(text: str | None) -> bool:
    return bool(text and text in {TEXT["uk"]["cancel"], TEXT["ru"]["cancel"]})


def _is_skip(text: str | None) -> bool:
    return bool(text and text in {TEXT["uk"]["skip"], TEXT["ru"]["skip"]})


async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    lang = user_language(update, context)
    context.user_data["appointment"] = {}
    await update.effective_message.reply_text(
        "Як до вас звертатися?" if lang == "uk" else "Как к вам обращаться?",
        reply_markup=cancel_keyboard(lang),
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _is_cancel(text): return await cancel(update, context)
    if not 2 <= len(text) <= 80:
        await update.effective_message.reply_text("Вкажіть ім'я від 2 до 80 символів." if lang == "uk" else "Укажите имя от 2 до 80 символов.")
        return NAME
    context.user_data["appointment"]["patient_name"] = text
    await update.effective_message.reply_text(
        "Надішліть український номер телефону." if lang == "uk" else "Отправьте украинский номер телефона.",
        reply_markup=cancel_keyboard(lang, contact=True),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = user_language(update, context)
    raw = update.effective_message.contact.phone_number if update.effective_message.contact else update.effective_message.text
    if _is_cancel(raw): return await cancel(update, context)
    phone = normalize_ua_phone(raw or "")
    if not phone:
        await update.effective_message.reply_text("Невірний номер. Формат: +380XXXXXXXXX або 0XXXXXXXXX." if lang == "uk" else "Неверный номер. Формат: +380XXXXXXXXX или 0XXXXXXXXX.")
        return PHONE
    context.user_data["appointment"]["phone"] = phone
    await update.effective_message.reply_text("Яка послуга вас цікавить?" if lang == "uk" else "Какая услуга вас интересует?", reply_markup=cancel_keyboard(lang))
    return SERVICE


async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _is_cancel(text): return await cancel(update, context)
    context.user_data["appointment"]["service"] = text[:200]
    await update.effective_message.reply_text("Бажана дата? Наприклад, 25.06. Можна пропустити." if lang == "uk" else "Желаемая дата? Например, 25.06. Можно пропустить.", reply_markup=cancel_keyboard(lang, skip=True))
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _is_cancel(text): return await cancel(update, context)
    context.user_data["appointment"]["preferred_date"] = None if _is_skip(text) else text[:80]
    await update.effective_message.reply_text("Бажаний час? Можна пропустити." if lang == "uk" else "Желаемое время? Можно пропустить.", reply_markup=cancel_keyboard(lang, skip=True))
    return TIME


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _is_cancel(text): return await cancel(update, context)
    context.user_data["appointment"]["preferred_time"] = None if _is_skip(text) else text[:80]
    await update.effective_message.reply_text("Додатковий коментар? Можна пропустити." if lang == "uk" else "Дополнительный комментарий? Можно пропустить.", reply_markup=cancel_keyboard(lang, skip=True))
    return COMMENT


async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _is_cancel(text): return await cancel(update, context)
    data = context.user_data["appointment"]
    data["comment"] = None if _is_skip(text) else text[:500]
    summary = (
        f"<b>Перевірте заявку</b>\nІм'я: {safe_html(data['patient_name'])}\nТелефон: <code>{safe_html(data['phone'])}</code>\n"
        f"Послуга: {safe_html(data['service'])}\nДата: {safe_html(data.get('preferred_date') or 'не вказана')}\n"
        f"Час: {safe_html(data.get('preferred_time') or 'не вказано')}\nКоментар: {safe_html(data.get('comment') or '—')}"
        if lang == "uk" else
        f"<b>Проверьте заявку</b>\nИмя: {safe_html(data['patient_name'])}\nТелефон: <code>{safe_html(data['phone'])}</code>\n"
        f"Услуга: {safe_html(data['service'])}\nДата: {safe_html(data.get('preferred_date') or 'не указана')}\n"
        f"Время: {safe_html(data.get('preferred_time') or 'не указано')}\nКомментарий: {safe_html(data.get('comment') or '—')}"
    )
    await update.effective_message.reply_text(summary, parse_mode="HTML", reply_markup=confirmation_keyboard(lang, "appt"))
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang, action = user_language(update, context), query.data.rsplit(":", 1)[1]
    if action == "change":
        context.user_data["appointment"] = {}
        await query.edit_message_text("Введіть ім'я ще раз." if lang == "uk" else "Введите имя ещё раз.")
        return NAME
    if action == "cancel":
        context.user_data.pop("appointment", None)
        await query.edit_message_text("Заявку скасовано." if lang == "uk" else "Заявка отменена.")
        await query.message.reply_text("Головне меню" if lang == "uk" else "Главное меню", reply_markup=main_menu(lang))
        return ConversationHandler.END
    data = context.user_data["appointment"]
    db = context.application.bot_data["db"]
    try:
        profile = await db.upsert_profile(update.effective_user, lang)
        record = await db.create_appointment(profile["id"], AppointmentInput(**data))
        await context.application.bot_data["notifications"].notify(
            context.bot, "appointment", record, profile
        )
    except Exception:
        await query.edit_message_text("Не вдалося зберегти заявку. Спробуйте пізніше." if lang == "uk" else "Не удалось сохранить заявку. Попробуйте позже.")
        return ConversationHandler.END
    context.user_data.pop("appointment", None)
    await query.edit_message_text(
        (f"✅ Заявку {record['public_id']} прийнято. Це попередня заявка. Адміністратор клініки зв'яжеться з вами для підтвердження дати й часу."
         if lang == "uk" else
         f"✅ Заявка {record['public_id']} принята. Это предварительная заявка. Администратор клиники свяжется с вами для подтверждения даты и времени.")
    )
    await query.message.reply_text("Головне меню" if lang == "uk" else "Главное меню", reply_markup=main_menu(lang))
    return ConversationHandler.END


def conversation() -> ConversationHandler:
    book_pattern = r"^(Записатися на прийом|Записаться на приём)$"
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(book_pattern), begin),
            CallbackQueryHandler(begin, pattern=r"^quick:book$"),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, get_phone)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern=r"^appt:(confirm|change|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
