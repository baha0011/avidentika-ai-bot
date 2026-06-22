# Website AI assistant

Этот слой добавляет к существующему Telegram AI-администратору Web API и embeddable-виджет для сайта. Telegram-бот остаётся каналом администратора: заявки с сайта отправляются в админский чат отдельной карточкой с пометкой `Источник: сайт`.

## Архитектура

```text
Website widget -> FastAPI -> AIService / KnowledgeService -> Supabase pgvector
                         -> WebRequestService -> Supabase appointments/support_requests
                         -> Telegram admin notification
```

Сайт не получает серверные ключи. Все ключи остаются только в `.env` на сервере.

## Новые файлы

- `app/api/main.py` — точка входа FastAPI.
- `app/api/schemas.py` — Pydantic-схемы запросов и ответов.
- `app/api/helpers.py` — определение языка и быстрые действия.
- `app/services/web_request_service.py` — создание web-профиля, заявки и обращения.
- `app/services/web_notification_service.py` — Telegram-карточки для заявок с сайта.
- `app/web_widget/static/widget.js` — встраиваемый виджет.
- `app/web_widget/static/widget.css` — стили виджета.
- `app/web_widget/static/index.html` — demo-страница.
- `supabase/migrations/004_website_assistant.sql` — расширение схемы для website source и web-session.

## Запуск API локально

```bash
pip install -r requirements.txt
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/session
```

Demo-страница виджета будет доступна по адресу:

```text
http://localhost:8000/
```

## Docker

```bash
docker compose up -d --build bot api
```

- `bot` запускает Telegram long polling.
- `api` запускает FastAPI на порту `8000`.

## Webflow / сайт

Вставка одной строкой перед закрывающим `</body>`:

```html
<script src="https://DOMAIN/static/widget.js" data-api-base="https://DOMAIN"></script>
```

Для Webflow: Page settings или Project settings → Custom Code → Footer Code.

## CORS

На сервере укажите домены сайта через переменную окружения `CORS_ALLOWED_ORIGINS`, например:

```dotenv
CORS_ALLOWED_ORIGINS=https://avidentika.com.ua,https://www.avidentika.com.ua
```

Не ставьте `*` для production.

## Supabase migration

Перед приёмом заявок с сайта примените:

```text
supabase/migrations/004_website_assistant.sql
```

Миграция не удаляет старые данные и не ломает Telegram-заявки. Она добавляет `source`, `web_session_id`, `contact_method`, `telegram_username`, `created_from_url`, `user_agent` и поле врача для web-заявок.

## Ограничения

- AI отвечает только по базе знаний клиники.
- AI не ставит диагнозы и не назначает лечение.
- При острой боли, отёке, температуре или травме пользователь должен обратиться за срочной медицинской помощью.
- Дата и время записи считаются предварительными, администратор подтверждает их вручную.
