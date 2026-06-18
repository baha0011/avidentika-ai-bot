import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


async def send_due_reminders(context) -> None:
    db = context.application.bot_data["db"]
    notifications = context.application.bot_data["notifications"]
    now = datetime.now(UTC)
    try:
        records = await db.list_due_reminders(now.isoformat(), (now + timedelta(hours=24)).isoformat())
    except Exception:
        logger.exception("Could not load due reminders")
        return
    for record in records:
        try:
            profile = await db.get_profile_notification_target(record["user_id"])
            await notifications.send_visit_reminder(context.bot, record, profile)
        except Exception as exc:
            logger.warning("Reminder delivery failed for %s: %s", record["public_id"], type(exc).__name__)
        finally:
            try:
                await db.mark_reminder_sent(record["public_id"])
            except Exception:
                logger.warning("Could not mark reminder attempt for %s", record["public_id"])
