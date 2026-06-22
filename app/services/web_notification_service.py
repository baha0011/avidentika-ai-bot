from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.security import safe_html


def web_admin_actions_keyboard(kind: str, public_id: str, status: str = "new") -> InlineKeyboardMarkup:
    if status == "new":
        rows = [[
            InlineKeyboardButton("Взять в работу", callback_data=f"adm:{kind}:{public_id}:in_progress"),
            InlineKeyboardButton("Отклонить", callback_data=f"adm:{kind}:{public_id}:cancelled"),
        ]]
    else:
        rows = []
    if kind == "appointment":
        rows.append([InlineKeyboardButton("✅ Подтвердить запись", callback_data=f"admconfirm:appointment:{public_id}")])
    rows.append([InlineKeyboardButton("Закрыть", callback_data=f"adm:{kind}:{public_id}:closed")])
    if _can_reply(record_public_id=public_id):
        rows.append([InlineKeyboardButton("💬 Написать клиенту", callback_data=f"admreply:{kind}:{public_id}")])
    return InlineKeyboardMarkup(rows)


async def notify_admin_website_request(bot, admin_chat_id: int, kind: str, record: dict, profile: dict | None = None) -> None:
    is_appointment = kind == "appointment"
    title = "🦷 Новая заявка на приём" if is_appointment else "💬 Новое обращение"
    telegram_username = record.get("telegram_username") or (profile or {}).get("username") or "не указан"
    lines = [
        f"<b>{title}</b>",
        f"Номер заявки: <code>{safe_html(record.get('public_id'))}</code>",
        "Источник: <b>сайт</b>",
        f"Имя: {safe_html(record.get('patient_name'))}",
        f"Телефон: <code>{safe_html(record.get('phone'))}</code>",
        f"Telegram: {safe_html('@' + telegram_username.lstrip('@')) if telegram_username != 'не указан' else 'не указан'}",
    ]
    if is_appointment:
        lines.extend([
            f"Услуга: {safe_html(record.get('service'))}",
            f"Дата: {safe_html(record.get('preferred_date') or 'не указана')}",
            f"Время: {safe_html(record.get('preferred_time') or 'не указано')}",
            f"Врач: {safe_html(record.get('doctor') or record.get('confirmed_doctor') or 'не выбран')}",
            f"Комментарий: {safe_html(record.get('comment') or '—')}",
        ])
    else:
        lines.append(f"Вопрос: {safe_html(record.get('question'))}")
    lines.append(f"Статус: <b>{safe_html(record.get('status') or 'new')}</b>")
    await bot.send_message(
        chat_id=admin_chat_id,
        text="\n".join(lines),
        parse_mode="HTML",
        reply_markup=web_admin_actions_keyboard(kind, record["public_id"], record.get("status", "new")),
    )


def _can_reply(record_public_id: str) -> bool:
    # Keep the Telegram admin flow visible. For website-only users the handler will
    # still be unable to deliver a bot message unless the user later starts Telegram.
    return bool(record_public_id)
