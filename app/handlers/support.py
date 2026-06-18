from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.handlers.start import cancel, user_language
from app.keyboards.keyboards import TEXT, cancel_keyboard, confirmation_keyboard, main_menu
from app.models.schemas import SupportInput
from app.utils.phone import normalize_ua_phone
from app.utils.security import safe_html

NAME, PHONE, QUESTION, CONFIRM = range(20, 24)


def _cancelled(text: str | None) -> bool:
    return bool(text and text in {TEXT["uk"]["cancel"], TEXT["ru"]["cancel"]})


async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = user_language(update, context)
    context.user_data["support"] = {}
    await update.effective_message.reply_text("Як до вас звертатися?" if lang == "uk" else "Как к вам обращаться?", reply_markup=cancel_keyboard(lang))
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _cancelled(text): return await cancel(update, context)
    if not 2 <= len(text) <= 80:
        await update.effective_message.reply_text("Вкажіть коректне ім'я." if lang == "uk" else "Укажите корректное имя.")
        return NAME
    context.user_data["support"]["patient_name"] = text
    await update.effective_message.reply_text("Надішліть номер телефону." if lang == "uk" else "Отправьте номер телефона.", reply_markup=cancel_keyboard(lang, contact=True))
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = user_language(update, context)
    raw = update.effective_message.contact.phone_number if update.effective_message.contact else update.effective_message.text
    if _cancelled(raw): return await cancel(update, context)
    phone = normalize_ua_phone(raw or "")
    if not phone:
        await update.effective_message.reply_text("Невірний номер. Формат: +380XXXXXXXXX або 0XXXXXXXXX." if lang == "uk" else "Неверный номер. Формат: +380XXXXXXXXX или 0XXXXXXXXX.")
        return PHONE
    context.user_data["support"]["phone"] = phone
    await update.effective_message.reply_text("Напишіть ваше питання." if lang == "uk" else "Напишите ваш вопрос.", reply_markup=cancel_keyboard(lang))
    return QUESTION


async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang, text = user_language(update, context), update.effective_message.text.strip()
    if _cancelled(text): return await cancel(update, context)
    if not 3 <= len(text) <= 1000:
        await update.effective_message.reply_text("Питання має містити від 3 до 1000 символів." if lang == "uk" else "Вопрос должен содержать от 3 до 1000 символов.")
        return QUESTION
    data = context.user_data["support"]
    data["question"] = text
    summary = (
        f"<b>Перевірте звернення</b>\nІм'я: {safe_html(data['patient_name'])}\nТелефон: <code>{safe_html(data['phone'])}</code>\nПитання: {safe_html(text)}"
        if lang == "uk" else
        f"<b>Проверьте обращение</b>\nИмя: {safe_html(data['patient_name'])}\nТелефон: <code>{safe_html(data['phone'])}</code>\nВопрос: {safe_html(text)}"
    )
    await update.effective_message.reply_text(summary, parse_mode="HTML", reply_markup=confirmation_keyboard(lang, "support"))
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang, action = user_language(update, context), query.data.rsplit(":", 1)[1]
    if action == "change":
        context.user_data["support"] = {}
        await query.edit_message_text("Введіть ім'я ще раз." if lang == "uk" else "Введите имя ещё раз.")
        return NAME
    if action == "cancel":
        context.user_data.pop("support", None)
        await query.edit_message_text("Звернення скасовано." if lang == "uk" else "Обращение отменено.")
        return ConversationHandler.END
    data = context.user_data["support"]
    db = context.application.bot_data["db"]
    try:
        profile = await db.upsert_profile(update.effective_user, lang)
        record = await db.create_support_request(profile["id"], SupportInput(**data))
        await context.application.bot_data["notifications"].notify(context.bot, "support", record)
    except Exception:
        await query.edit_message_text("Не вдалося передати звернення. Спробуйте пізніше." if lang == "uk" else "Не удалось передать обращение. Попробуйте позже.")
        return ConversationHandler.END
    context.user_data.pop("support", None)
    await query.edit_message_text(
        f"✅ Звернення {record['public_id']} передано адміністратору." if lang == "uk" else f"✅ Обращение {record['public_id']} передано администратору."
    )
    await query.message.reply_text("Головне меню" if lang == "uk" else "Главное меню", reply_markup=main_menu(lang))
    return ConversationHandler.END


def conversation() -> ConversationHandler:
    pattern = r"^(Зв'язатися з адміністратором|Связаться с администратором)$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), begin)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, get_phone)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_question)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern=r"^support:(confirm|change|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
