from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.keyboards import client_actions_keyboard, client_main_menu_keyboard
from app.utils.security import safe_html


def telegram_account_html(profile: dict | None) -> str:
    if not profile:
        return "не указан"
    username = str(profile.get("username") or "").lstrip("@").strip()
    if username:
        return f"@{safe_html(username)}"
    telegram_user_id = profile.get("telegram_user_id")
    if telegram_user_id is not None:
        return f"ID: <code>{safe_html(telegram_user_id)}</code>"
    return "не указан"


def admin_actions_keyboard(kind: str, public_id: str, status: str) -> InlineKeyboardMarkup | None:
    if status == "new":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Взять в работу", callback_data=f"adm:{kind}:{public_id}:in_progress"),
            InlineKeyboardButton("Отклонить", callback_data=f"adm:{kind}:{public_id}:cancelled"),
        ]])
    if status == "in_progress":
        rows = []
        if kind == "appointment":
            rows.append([InlineKeyboardButton(
                "✅ Подтвердить запись", callback_data=f"admconfirm:appointment:{public_id}"
            )])
        rows.append([InlineKeyboardButton(
            "💬 Написать клиенту", callback_data=f"admreply:{kind}:{public_id}"
        )])
        rows.append([
            InlineKeyboardButton("Закрыть заявку", callback_data=f"adm:{kind}:{public_id}:closed"),
            InlineKeyboardButton("Отклонить", callback_data=f"adm:{kind}:{public_id}:cancelled"),
        ])
        return InlineKeyboardMarkup(rows)
    if status == "confirmed":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Написать клиенту", callback_data=f"admreply:{kind}:{public_id}")],
            [InlineKeyboardButton("Закрыть заявку", callback_data=f"adm:{kind}:{public_id}:closed")],
        ])
    return None


class NotificationService:
    def __init__(self, admin_chat_id: int) -> None:
        self.admin_chat_id = admin_chat_id

    async def notify(self, bot, kind: str, record: dict, profile: dict | None = None) -> None:
        is_appointment = kind == "appointment"
        title = "🦷 Новая заявка на приём" if is_appointment else "💬 Новое обращение"
        details = [
            f"<b>{title}</b>",
            f"Номер: <code>{safe_html(record['public_id'])}</code>",
            f"Имя: {safe_html(record.get('patient_name'))}",
            f"Телефон: <code>{safe_html(record.get('phone'))}</code>",
            f"Telegram: {telegram_account_html(profile)}",
        ]
        if is_appointment:
            details.extend([
                f"Услуга: {safe_html(record.get('service'))}",
                f"Дата: {safe_html(record.get('preferred_date') or 'не указана')}",
                f"Время: {safe_html(record.get('preferred_time') or 'не указано')}",
                f"Доктор: {safe_html(record.get('confirmed_doctor') or 'не назначен')}",
                f"Комментарий: {safe_html(record.get('comment') or '—')}",
            ])
        else:
            details.append(f"Вопрос: {safe_html(record.get('question'))}")
        details.append("Статус: <b>new</b>")
        keyboard = admin_actions_keyboard(kind, record["public_id"], "new")
        await bot.send_message(
            chat_id=self.admin_chat_id,
            text="\n".join(details),
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    async def notify_client_status(self, bot, record: dict, profile: dict) -> None:
        language = profile.get("preferred_language")
        language = language if language in {"uk", "ru"} else "uk"
        public_id = record["public_id"]
        status = record["status"]
        messages = {
            "ru": {
                "in_progress": f"✅ Администратор взял вашу заявку {public_id} в работу. Скоро с вами свяжутся.",
                "closed": f"✅ Ваша заявка {public_id} закрыта администратором.",
                "cancelled": (
                    f"❌ Ваша заявка {public_id} отклонена. Для уточнения нажмите “Связаться с администратором” "
                    "или позвоните +38 066 200 05 23."
                ),
            },
            "uk": {
                "in_progress": f"✅ Адміністратор взяв вашу заявку {public_id} у роботу. Незабаром з вами зв’яжуться.",
                "closed": f"✅ Вашу заявку {public_id} закрито адміністратором.",
                "cancelled": (
                    f"❌ Вашу заявку {public_id} відхилено. Для уточнення натисніть “Зв'язатися з адміністратором” "
                    "або зателефонуйте +38 066 200 05 23."
                ),
            },
        }
        if status not in messages[language]:
            raise ValueError(f"Unsupported notification status: {status}")
        await bot.send_message(
            chat_id=int(profile["telegram_user_id"]),
            text=messages[language][status],
            reply_markup=client_main_menu_keyboard(language),
        )

    async def notify_client_message(self, bot, record: dict, profile: dict, message: str) -> None:
        language = profile.get("preferred_language")
        language = language if language in {"uk", "ru"} else "uk"
        title = (
            f"💬 Повідомлення від адміністратора AVIDENTIKA щодо заявки {record['public_id']}:"
            if language == "uk" else
            f"💬 Сообщение от администратора AVIDENTIKA по заявке {record['public_id']}:"
        )
        await bot.send_message(
            chat_id=int(profile["telegram_user_id"]),
            text=f"{title}\n\n{message}",
            reply_markup=client_actions_keyboard(language),
        )

    async def notify_appointment_confirmation(self, bot, record: dict, profile: dict) -> None:
        language = profile.get("preferred_language")
        language = language if language in {"uk", "ru"} else "uk"
        comment = record.get("confirmation_comment")
        if language == "uk":
            lines = [
                f"✅ Ваш запис {record['public_id']} підтверджено!",
                f"📅 Дата: {record['confirmed_date']}",
                f"🕐 Час: {record['confirmed_time']}",
                f"🦷 Процедура: {record['confirmed_service']}",
                f"👨‍⚕️ Лікар: {record['confirmed_doctor']}",
                "📍 Київ, вул. Академіка Булаховського, 5-Б",
            ]
            if comment:
                lines.append(f"💬 Коментар: {comment}")
            lines.append("Якщо плани зміняться, зателефонуйте: +38 066 200 05 23.")
        else:
            lines = [
                f"✅ Ваша запись {record['public_id']} подтверждена!",
                f"📅 Дата: {record['confirmed_date']}",
                f"🕐 Время: {record['confirmed_time']}",
                f"🦷 Процедура: {record['confirmed_service']}",
                f"👨‍⚕️ Врач: {record['confirmed_doctor']}",
                "📍 Киев, ул. Академика Булаховского, 5-Б",
            ]
            if comment:
                lines.append(f"💬 Комментарий: {comment}")
            lines.append("Если планы изменятся, позвоните: +38 066 200 05 23.")
        await bot.send_message(
            chat_id=int(profile["telegram_user_id"]),
            text="\n".join(lines),
            reply_markup=client_actions_keyboard(language),
        )

    async def send_visit_reminder(self, bot, record: dict, profile: dict) -> None:
        lang = profile.get("preferred_language") if profile.get("preferred_language") in {"uk", "ru"} else "uk"
        text = (
            f"⏰ Нагадуємо про візит до AVIDENTIKA завтра.\n\n📅 {record['confirmed_date']} о {record['confirmed_time']}\n"
            f"🦷 {record['confirmed_service']}\n👨‍⚕️ {record['confirmed_doctor']}"
            if lang == "uk" else
            f"⏰ Напоминаем о визите в AVIDENTIKA завтра.\n\n📅 {record['confirmed_date']} в {record['confirmed_time']}\n"
            f"🦷 {record['confirmed_service']}\n👨‍⚕️ {record['confirmed_doctor']}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Підтвердити візит" if lang == "uk" else "✅ Подтвердить визит", callback_data=f"visit:{record['public_id']}:confirm")],
            [InlineKeyboardButton("🔄 Перенести" if lang == "uk" else "🔄 Перенести", callback_data=f"visit:{record['public_id']}:reschedule")],
            [InlineKeyboardButton("❌ Скасувати" if lang == "uk" else "❌ Отменить", callback_data=f"visit:{record['public_id']}:cancel")],
        ])
        await bot.send_message(chat_id=int(profile["telegram_user_id"]), text=text, reply_markup=keyboard)

    async def request_rating(self, bot, record: dict, profile: dict) -> None:
        lang = profile.get("preferred_language") if profile.get("preferred_language") in {"uk", "ru"} else "uk"
        text = "Оцініть, будь ласка, ваш візит до AVIDENTIKA від 1 до 5 ⭐" if lang == "uk" else "Оцените, пожалуйста, ваш визит в AVIDENTIKA от 1 до 5 ⭐"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(str(value), callback_data=f"rate:{record['public_id']}:{value}")
            for value in range(1, 6)
        ]])
        await bot.send_message(chat_id=int(profile["telegram_user_id"]), text=text, reply_markup=keyboard)

    async def notify_admin_event(self, bot, record: dict, event: str) -> None:
        await bot.send_message(
            chat_id=self.admin_chat_id,
            text=f"🔔 Заявка {record['public_id']}\n{event}\nКлиент: {safe_html(record.get('patient_name') or '—')}\nТелефон: {safe_html(record.get('phone') or '—')}",
            parse_mode="HTML",
            reply_markup=admin_actions_keyboard("appointment", record["public_id"], record.get("status", "in_progress")),
        )
