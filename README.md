# AI-администратор стоматологии AVIDENTIKA

AI-администратор для стоматологии AVIDENTIKA: Telegram-бот для клиентов и администраторов + сайт-виджет с AI-помощником, заявками, обращениями к администратору и синхронизацией с Google Sheets.

Проект консультирует пациентов только по базе знаний клиники, помогает оставить предварительную заявку, передаёт её администратору в Telegram и сохраняет данные в Supabase/PostgreSQL. Для сайта есть FastAPI API и встраиваемый JavaScript-виджет.

> Это демо, а не медицинская система. AI не ставит диагнозы, не назначает лечение и не подтверждает запись. Окончательные дату и время подтверждает администратор клиники.

## Что умеет

### Telegram-бот

- украинский и русский интерфейс с автоматическим определением языка;
- ответы по услугам, ценам, врачам, адресу и графику через RAG;
- безопасная AI-навигация к подходящему направлению и врачу без постановки диагноза;
- честный отказ, если фактов нет в базе знаний;
- предупреждение при признаках потенциально неотложного состояния;
- предварительная запись с проверкой украинского номера телефона;
- обращение к администратору;
- админ-панель с командами `/admin`, `/new`, `/today`, `/tomorrow`, `/find`;
- постоянная нижняя кнопка `⚙️ Админ-панель` в Telegram;
- статусы `new`, `in_progress`, `confirmed`, `closed`, `cancelled`;
- подтверждение записи с датой, временем, процедурой, врачом и комментарием;
- напоминание за 24 часа до подтверждённого визита;
- подтверждение, перенос и отмена визита клиентом;
- оценка визита 1–5 и текстовый отзыв;
- свободное сообщение администратора клиенту.

### Сайт-виджет

- отдельный AI-ассистент для сайта / Webflow;
- запуск через FastAPI (`uvicorn app.api.main:app`);
- встраивание одной строкой `<script>`;
- кнопки `Записаться на приём`, `Задать вопрос`, `Связаться с администратором`, `Услуги`, `Врачи`, `Цены`, `Контакты`;
- форма заявки прямо на сайте;
- форма связи с администратором;
- поддержка телефонных форматов `+380 99 561 48 49`, `+38 (099)561-67-34`, `099 561 48 49`;
- защита от повторной отправки формы двойным кликом;
- серверная защита от дублей одинаковых заявок за короткий период;
- доставка ответов администратора в чат сайта, если клиент оставил заявку с сайта;
- уведомления о новых заявках в админский Telegram-чат;
- responsive-дизайн для телефона и десктопа.

### База и интеграции

- Supabase/PostgreSQL как основная база;
- pgvector-поиск + резервный полнотекстовый поиск PostgreSQL;
- Google Sheets как рабочее зеркало заявок и истории;
- Docker Compose для отдельного запуска `bot` и `api`;
- тесты без реальных запросов к OpenAI, Telegram и Supabase;
- защита от prompt injection и утечки внутренних инструкций.

## Архитектура

```text
Telegram client/admin
        ↓
Telegram handlers → AIService → KnowledgeService → Supabase/pgvector
        ↓              ↓
NotificationService   SupabaseService → appointments/support_requests/profiles
        ↓
Telegram admin chat

Website/Webflow
        ↓
static widget.js → FastAPI app.api.main
        ↓              ↓
WebRequestService     WebNotificationStore
        ↓              ↓
Supabase              website chat notifications
        ↓
GoogleSheetsService → Apps Script Web App → Google Sheets
```

`SUPABASE_SERVICE_ROLE_KEY`, Telegram token, OpenAI key and Google Sheets secret are used only server-side. Do not put them into browser code, public repositories or logs.

## Основные API сайта

FastAPI поднимает endpoints:

```text
GET  /health
GET  /api/session
POST /api/chat
POST /api/appointments
POST /api/support
GET  /api/notifications
```

Статические файлы виджета доступны через:

```text
/static/widget.js
/static/widget.css
```

## 1. Создание Telegram-бота

1. Откройте в Telegram `@BotFather`.
2. Отправьте `/newbot`.
3. Укажите название и username, который заканчивается на `bot`.
4. Скопируйте токен — это значение для переменной Telegram-токена в `.env`.
5. Никому не отправляйте токен. При утечке перевыпустите его через BotFather.

Чтобы узнать ID админского чата:

1. Добавьте бота в администраторский чат или напишите ему лично.
2. Отправьте любое сообщение.
3. Временно откройте метод `getUpdates` для своего бота.
4. Найдите `message.chat.id`. Для группы значение обычно отрицательное.
5. Если бот работает в группе, дайте ему право отправлять сообщения.

После получения ID не сохраняйте URL с токеном и очистите историю браузера.

## 2. Supabase

1. Создайте проект Supabase.
2. В **Project Settings → API** скопируйте Project URL.
3. Скопируйте серверный `service_role` key.
4. В **SQL Editor** примените миграции по порядку.

Миграции:

```text
supabase/migrations/001_initial_schema.sql
supabase/migrations/002_appointment_confirmation.sql
supabase/migrations/003_reminders_reschedule_reviews.sql
supabase/migrations/004_website_assistant.sql
supabase/migrations/005_web_messages.sql
```

`001_initial_schema.sql` создаёт основную схему, RLS, pgvector-функции и таблицы базы знаний.  
`004_website_assistant.sql` добавляет поля для сайта: `source`, `web_session_id`, `telegram_username`, `doctor`, `created_from_url`.  
`005_web_messages.sql` добавляет сообщения сайта, чтобы администратор мог отвечать в чат виджета.

Если база уже была создана раньше, всё равно выполните миграции `004` и `005` вручную в SQL Editor.

## 3. OpenAI API

Создайте API key в OpenAI Platform и сохраните его в `.env`.

По умолчанию используются:

```dotenv
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Схема рассчитана на embeddings размерности `1536`, которую возвращает `text-embedding-3-small`.

## 4. Локальная установка

Требуется Python 3.11 или новее.

```bash
git clone https://github.com/baha0011/avidentika-ai-bot.git
cd avidentika-ai-bot
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Если `python3.11` не найден на macOS:

```bash
brew install python@3.11
"$(brew --prefix python@3.11)/bin/python3.11" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Заполните `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=токен_бота
ADMIN_CHAT_ID=числовой_id_админ_чата
OPENAI_API_KEY=секретный_openai_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=секретный_service_role_key

CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
WIDGET_PUBLIC_BASE_URL=http://localhost:8000

GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_WEB_APP_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
GOOGLE_SHEETS_WEBHOOK_SECRET=секрет_для_apps_script
```

`.env` уже добавлен в `.gitignore`. Не коммитьте его.

## 5. Обновление базы знаний

После применения SQL-схемы и заполнения `.env` выполните:

```bash
python scripts/update_knowledge.py
```

Скрипт:

- обходит сайт AVIDENTIKA;
- очищает технический текст;
- нарезает страницы на фрагменты;
- создаёт embeddings через OpenAI;
- сохраняет знания в Supabase;
- ведёт журнал в `knowledge_update_logs`;
- сохраняет локальный отчёт `data/knowledge_update_report.json`.

Не запускайте несколько копий обновления одновременно. Обычно достаточно запускать его после изменения сайта или раз в сутки.

## 6. Запуск Telegram-бота

```bash
python bot.py
```

При верной конфигурации бот запустит long polling. Для остановки нажмите `Ctrl+C`.

Команды клиента:

- `/start` — главное меню;
- `/help` — краткая помощь;
- `/cancel` — отмена текущего сценария;
- `/privacy` — сведения о данных и ограничениях демо.

Команды администратора:

- `/admin` — панель с кнопками «Новые заявки», «Сегодня», «Завтра»;
- `/today` — подтверждённые записи на сегодня;
- `/tomorrow` — записи на завтра;
- `/new` — новые заявки и обращения;
- `/find A-1234ABCD` — поиск по номеру заявки.

## 7. Запуск сайта/API

В отдельном терминале:

```bash
source .venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Демо-страница виджета:

```text
http://localhost:8000/
```

Проверка API-заявки:

```bash
curl -X POST http://localhost:8000/api/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"web-test-123",
    "patient_name":"Тест Клиент",
    "phone":"+38 (099) 561-48-49",
    "telegram_username":"test_user",
    "service":"Консультация",
    "preferred_date":"25.06.2026",
    "preferred_time":"14:00",
    "doctor":"Терапевт",
    "comment":"Тестовая заявка с сайта",
    "created_from_url":"http://localhost:8000"
  }'
```

## 8. Встраивание на сайт / Webflow

После деплоя API на публичный домен вставьте перед `</body>`:

```html
<script src="https://YOUR-DOMAIN/static/widget.js" data-api-base="https://YOUR-DOMAIN"></script>
```

Для Webflow:

1. Откройте **Project Settings → Custom Code** или настройки конкретной страницы.
2. Вставьте script в Footer Code / Before `</body>`.
3. Опубликуйте сайт.
4. Проверьте, что домен сайта добавлен в `CORS_ALLOWED_ORIGINS`.

Пример для продакшена:

```dotenv
CORS_ALLOWED_ORIGINS=https://avidentika.com.ua,https://www.avidentika.com.ua
WIDGET_PUBLIC_BASE_URL=https://api.your-domain.com
```

## 9. Docker

```bash
docker compose build
docker compose up -d
docker compose logs -f bot
docker compose logs -f api
```

Остановка:

```bash
docker compose down
```

Обновление базы знаний из контейнера:

```bash
docker compose run --rm bot python scripts/update_knowledge.py
```

`docker-compose.yml` содержит два сервиса:

- `bot` — Telegram long polling;
- `api` — FastAPI для сайта и виджета, порт `8000`.

## 10. Google Sheets

Google Sheets работает как рабочее зеркало. Supabase остаётся основной базой: если Google временно недоступен, заявка всё равно сохраняется в Supabase.

Интеграция использует бесплатный Google Apps Script. Google Cloud, Service Account, JSON key и биллинг не нужны.

Листы:

- `Записи` — одна строка на заявку, обновление по `public_id`;
- `История клиентов` — история действий отдельными строками.

Актуальный код Apps Script и тест `curl` находятся здесь:

```text
docs/google-sheets-webhook.md
```

После изменения Apps Script всегда создавайте новую версию деплоя:

```text
Deploy → Manage deployments → Edit → Version: New version → Deploy
```

Проверка webhook:

```bash
WEBAPP=$(grep '^GOOGLE_SHEETS_WEB_APP_URL=' .env | cut -d= -f2-)
SECRET=$(grep '^GOOGLE_SHEETS_WEBHOOK_SECRET=' .env | cut -d= -f2-)

curl -sS -L \
  -H "Content-Type: application/json" \
  -d "{\"webhook_secret\":\"$SECRET\",\"type\":\"appointment\",\"event\":\"Тест\",\"details\":\"Проверка curl\",\"record\":{\"public_id\":\"A-ABCDEF12\",\"source\":\"website\",\"status\":\"new\",\"patient_name\":\"Тест Клиент\",\"phone\":\"+380995614849\",\"telegram_username\":\"test_user\",\"service\":\"Консультация\",\"preferred_date\":\"25.06.2026\",\"preferred_time\":\"14:00\",\"doctor\":\"Терапевт\",\"comment\":\"Тест\"}}" \
  "$WEBAPP"
```

Ожидаемый ответ:

```json
{"ok":true}
```

## 11. Проверка полного сценария

### Telegram

1. Отправьте боту `/start`.
2. Нажмите «Записаться на приём».
3. Введите имя, телефон, услугу, дату, время и комментарий.
4. Убедитесь, что в Supabase появилась строка `appointments` со статусом `new`.
5. В админском Telegram-чате проверьте карточку заявки.
6. Нажмите «Взять в работу».
7. Нажмите «Подтвердить запись» и введите дату, время, процедуру, врача и комментарий.
8. Проверьте статус `confirmed` и уведомление клиента.
9. После визита закройте заявку. Клиенту не отправляется отдельное сообщение о закрытии.

### Сайт

1. Откройте demo-страницу `http://localhost:8000/` или страницу Webflow с виджетом.
2. Нажмите `Записаться на приём`.
3. Заполните форму и отправьте.
4. Проверьте одну строку в Supabase `appointments`.
5. Проверьте одну карточку в админском Telegram-чате.
6. Проверьте одну строку в Google Sheets `Записи`.
7. Нажмите в Telegram «Написать клиенту» — сообщение должно прийти в чат сайта через polling `/api/notifications`.

## 12. Очистка данных для нового теста

Очистить заявки, клиентов, обращения, историю чата и сообщения сайта, но оставить базу знаний ИИ:

```sql
truncate table
  public.web_messages,
  public.conversations,
  public.appointments,
  public.support_requests,
  public.profiles
restart identity cascade;
```

Не очищайте `knowledge_documents`, если хотите сохранить базу знаний AI.

Для Google Sheets используйте Apps Script функцию из `docs/google-sheets-webhook.md`:

```javascript
clearAvidentikaSheets()
```

Она очищает строки ниже заголовков на листах `Записи` и `История клиентов`.

## 13. Тесты и проверки

Тесты используют mocks и не отправляют запросы в OpenAI, Telegram или Supabase:

```bash
pytest -q
```

Проверка синтаксиса:

```bash
python -m compileall -q app bot.py scripts/update_knowledge.py
python -c "import bot; print('imports: OK')"
```

Проверка, что секреты случайно не попали в Git:

```bash
git grep -nE 'sk-[A-Za-z0-9_-]{20,}|service_role.*[A-Za-z0-9._-]{20,}|[0-9]{8,}:[A-Za-z0-9_-]{20,}' -- ':!.env.example' || true
git ls-files | grep -E '^\.env$|\.env'
git status --short
```

Нормально, если `git ls-files` показывает только `.env.example`.

## 14. Логи и безопасность

Логи содержат запуск, номера заявок, смену статусов и типы ошибок. API-ключи, service role, Telegram token и Google Sheets secret нельзя отправлять в чат и нельзя коммитить.

Меры безопасности:

- callback управления заявкой работает только в `ADMIN_CHAT_ID`;
- входные данные ограничены по длине;
- HTML экранируется перед отправкой в Telegram;
- OpenAI получает только релевантные фрагменты базы знаний;
- инструкции из документов считаются данными и не исполняются;
- RLS закрывает таблицы для `anon` и `authenticated`;
- browser-widget не получает серверные ключи;
- Google Sheets webhook принимает запись только с правильным secret.

Если Telegram token засветился в логах или чате, перевыпустите его в BotFather и обновите `.env`.

## 15. Развёртывание на сервере

Подойдёт VPS с Docker:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker "$USER"
```

После повторного входа:

```bash
git clone https://github.com/baha0011/avidentika-ai-bot.git
cd avidentika-ai-bot
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
docker compose logs -f api
```

Для сайта нужен публичный HTTPS-домен перед FastAPI. Можно поставить reverse proxy Nginx/Caddy и проксировать API на порт `8000`.

## 16. CRM и реальное расписание

Сейчас бот и сайт принимают предварительные заявки. Они не бронируют реальный слот в CRM.

Для полноценной CRM-интеграции нужен адаптер в `app/services`, который после успешного сохранения в Supabase:

1. получает доступные интервалы из API клиники/CRM;
2. временно блокирует выбранный слот;
3. создаёт запись идемпотентно по `public_id`;
4. синхронизирует статусы обратно в Supabase;
5. обрабатывает отмену и перенос;
6. учитывает часовой пояс `Europe/Kyiv`.

## Ограничения демо

- содержание зависит от актуальности базы знаний;
- без API расписания нельзя показать реальные свободные окна;
- AI и embeddings требуют доступного OpenAI API;
- автоматическое определение языка для очень коротких сообщений может выбрать украинский как безопасный язык по умолчанию;
- демо не заменяет медицинскую консультацию и требует проверки владельцем клиники перед промышленным использованием.

## Частые ошибки

- `401 Unauthorized` Telegram — проверьте Telegram token.
- `409 Conflict` Telegram — удалите активный webhook перед запуском polling.
- `429 Too Many Requests` OpenAI — исчерпана квота или не настроен биллинг.
- `command not found: uvicorn` — выполните `pip install -r requirements.txt` и запускайте `python -m uvicorn ...`.
- Google Sheets `unauthorized` — secret в `.env` и Apps Script не совпадает.
- Google Sheets `Invalid appointment ID` — тестовый `public_id` должен быть формата `A-ABCDEF12`.
- Дубли заявок — убедитесь, что подтянуты последние изменения виджета и backend с защитой от повторной отправки.

## Структура

```text
app/
  api/                      FastAPI API для сайта и виджета
  handlers/                 Telegram-сценарии
  services/                 OpenAI, Supabase, RAG, уведомления, Google Sheets
  prompts/                  системный промпт
  keyboards/                кнопки RU/UK
  models/                   модели данных
  utils/                    язык, телефон, защита и логи
  web_widget/static/        widget.js, widget.css, demo index.html
scripts/update_knowledge.py обновление базы знаний сайта
supabase/migrations/        миграции PostgreSQL
supabase_schema.sql         SQL для Supabase Editor
docs/website-assistant.md   подробности сайта/API/виджета
docs/google-sheets-webhook.md актуальный Apps Script для Google Sheets
tests/                      автономные unit-тесты
bot.py                      точка запуска Telegram-бота
docker-compose.yml          сервисы bot и api
```
