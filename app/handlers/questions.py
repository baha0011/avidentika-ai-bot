from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.handlers.start import user_language
from app.keyboards.keyboards import TEXT, main_menu, source_keyboard
from app.services.knowledge_service import KnowledgeSearchError

logger = logging.getLogger(__name__)

ADDRESS = {
    "uk": "📍 Київ, вул. Академіка Булаховського, 5-Б\n🕙 Пн–Пт: 10:00–20:00\nСб–Нд: за попереднім записом\n📞 +38 066 200 05 23",
    "ru": "📍 Киев, ул. Академика Булаховского, 5-Б\n🕙 Пн–Пт: 10:00–20:00\nСб–Вс: по предварительной записи\n📞 +38 066 200 05 23",
}


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    lang = user_language(update, context)
    text = message.text.strip()
    t = TEXT[lang]
    if text == t["ask"]:
        await message.reply_text("Напишіть ваше запитання." if lang == "uk" else "Напишите ваш вопрос.")
        return
    if text == t["address"]:
        await message.reply_text(ADDRESS[lang], reply_markup=main_menu(lang))
        return
    if text == t["services"]:
        text = "Які послуги та ціни є в клініці?" if lang == "uk" else "Какие услуги и цены есть в клинике?"
    settings = context.application.bot_data["settings"]
    limiter = context.application.bot_data["rate_limiter"]
    if len(text) > settings.max_message_length:
        await message.reply_text("Повідомлення надто довге." if lang == "uk" else "Сообщение слишком длинное.")
        return
    if not limiter.allow(update.effective_user.id):
        await message.reply_text("Забагато запитів. Спробуйте трохи пізніше." if lang == "uk" else "Слишком много запросов. Попробуйте немного позже.")
        return
    try:
        previous = context.user_data.get("last_question", "")
        lower_text = text.lower()

        follow_up_markers = (
            "это", "эта", "этот", "эти", "такое",
            "це", "ця", "цей", "ці", "таке",
        )

        is_follow_up = bool(previous) and (
            any(word in lower_text.split() for word in follow_up_markers)
            or lower_text.startswith(("а сколько", "а как", "а когда"))
        )

        question_for_ai = (
            f"{previous}\nУточнение пользователя: {text}"
            if is_follow_up else text
        )

        answer = await context.application.bot_data["ai"].answer(question_for_ai, lang)
        context.user_data["last_question"] = question_for_ai
        markup = source_keyboard(lang, answer.source_url) if answer.source_url else None
        await message.reply_text(answer.text, reply_markup=markup, disable_web_page_preview=True)
    except KnowledgeSearchError:
        logger.exception("Could not answer knowledge question")
        await message.reply_text(
            "Сервіс тимчасово недоступний. Спробуйте пізніше або зателефонуйте +38 066 200 05 23."
            if lang == "uk" else
            "Сервис временно недоступен. Попробуйте позже или позвоните +38 066 200 05 23."
        )
