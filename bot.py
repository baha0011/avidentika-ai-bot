from __future__ import annotations

import logging

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.config import ConfigurationError, load_settings
from app.handlers import admin, admin_commands, admin_conversations, appointments, client_visits, questions, start, support
from app.services.ai_service import AIService
from app.services.knowledge_service import KnowledgeService
from app.services.notification_service import NotificationService
from app.services.supabase_service import SupabaseService
from app.services.reminder_service import send_due_reminders
from app.services.google_sheets_service import GoogleSheetsService
from app.utils.logging import configure_logging
from app.utils.security import RateLimiter

logger = logging.getLogger(__name__)


async def on_error(update: object, context) -> None:
    logger.error("Unhandled Telegram update error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Сталася технічна помилка. Спробуйте пізніше.")
        except Exception:
            logger.exception("Could not send error response")


def build_application(settings=None) -> Application:
    settings = settings or load_settings()
    sheets = GoogleSheetsService(
        settings.google_sheets_enabled,
        settings.google_sheets_web_app_url,
        settings.google_sheets_webhook_secret,
        timeout_seconds=settings.http_timeout_seconds,
    )
    db = SupabaseService(settings.supabase_url, settings.supabase_service_role_key, sheets=sheets)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.http_timeout_seconds, max_retries=2)
    knowledge = KnowledgeService(
        db.client, openai_client, settings.openai_embedding_model,
        settings.rag_match_threshold, settings.rag_match_count,
    )
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(admin_commands.activate_persistent_panel)
        .build()
    )
    application.bot_data.update({
        "settings": settings,
        "db": db,
        "ai": AIService(openai_client, settings.openai_model, knowledge),
        "notifications": NotificationService(settings.admin_chat_id),
        "rate_limiter": RateLimiter(settings.rate_limit_requests, settings.rate_limit_period_seconds),
        "sheets": sheets,
    })
    application.add_handler(appointments.conversation())
    application.add_handler(support.conversation())
    application.add_handler(admin_conversations.conversation())
    application.add_handler(client_visits.conversation())
    application.add_handler(CallbackQueryHandler(
        client_visits.visit_action, pattern=r"^visit:A-[A-F0-9]{8}:(confirm|cancel)$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin.change_status,
        pattern=r"^adm:(appointment|support):[AS]-[A-F0-9]{8}:(in_progress|closed|cancelled)$",
    ))
    application.add_handler(CallbackQueryHandler(
        admin_commands.panel_action,
        pattern=r"^admin:list:(new|today|tomorrow)$",
    ))
    application.add_handler(CallbackQueryHandler(start.show_main_menu, pattern=r"^quick:menu$"))
    application.add_handler(CallbackQueryHandler(questions.prompt_question, pattern=r"^quick:ask$"))
    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(CommandHandler("help", start.help_command))
    application.add_handler(CommandHandler("cancel", start.cancel))
    application.add_handler(CommandHandler("privacy", start.privacy))
    application.add_handler(CommandHandler("today", admin_commands.today))
    application.add_handler(CommandHandler("tomorrow", admin_commands.tomorrow))
    application.add_handler(CommandHandler("new", admin_commands.new_requests))
    application.add_handler(CommandHandler("find", admin_commands.find_request))
    application.add_handler(CommandHandler("admin", admin_commands.panel))
    application.add_handler(MessageHandler(
        filters.Regex(r"^⚙️ Админ-панель$"), admin_commands.panel
    ))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, questions.handle_question))
    application.add_error_handler(on_error)
    if application.job_queue is None:
        raise RuntimeError("JobQueue недоступен. Установите зависимости из обновлённого requirements.txt")
    application.job_queue.run_repeating(send_due_reminders, interval=300, first=10, name="24h-reminders")
    return application


def main() -> None:
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Ошибка конфигурации: {exc}") from exc
    configure_logging(settings.log_level)
    logger.info("Starting AVIDENTIKA bot | env=%s", settings.app_env)
    build_application(settings).run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
