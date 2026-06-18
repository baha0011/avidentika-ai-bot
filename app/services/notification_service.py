from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.security import safe_html


class NotificationService:
    def __init__(self, admin_chat_id: int) -> None:
        self.admin_chat_id = admin_chat_id

    async def notify(self, bot, kind: str, record: dict) -> None:
        is_appointment = kind == "appointment"
        title = "🦷 Новая заявка на приём" if is_appointment else "💬 Новое обращение"
        details = [
            f"<b>{title}</b>",
            f"Номер: <code>{safe_html(record['public_id'])}</code>",
            f"Имя: {safe_html(record.get('patient_name'))}",
            f"Телефон: <code>{safe_html(record.get('phone'))}</code>",
        ]
        if is_appointment:
            details.extend([
                f"Услуга: {safe_html(record.get('service'))}",
                f"Дата: {safe_html(record.get('preferred_date') or 'не указана')}",
                f"Время: {safe_html(record.get('preferred_time') or 'не указано')}",
                f"Комментарий: {safe_html(record.get('comment') or '—')}",
            ])
        else:
            details.append(f"Вопрос: {safe_html(record.get('question'))}")
        details.append("Статус: <b>new</b>")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Взять в работу", callback_data=f"adm:{kind}:{record['public_id']}:in_progress"),
            InlineKeyboardButton("Закрыть заявку", callback_data=f"adm:{kind}:{record['public_id']}:closed"),
        ]])
        await bot.send_message(
            chat_id=self.admin_chat_id,
            text="\n".join(details),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
