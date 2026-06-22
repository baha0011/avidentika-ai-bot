# Google Sheets webhook

The bot mirrors website and Telegram requests to Google Sheets through a Google Apps Script Web App.

## Sheets

Create or use a spreadsheet with these sheets:

- `Записи`
- `История клиентов`

The script creates missing sheets and headers automatically.

## Apps Script

Open `Extensions -> Apps Script` in the Google spreadsheet and paste this script.

Replace:

- `CHANGE_ME` with the same value as `GOOGLE_SHEETS_WEBHOOK_SECRET` from `.env`
- `1LmrVATCwGPoDhJIebsHOjpvM35fDnaU_wWZzgov1WOw` with your spreadsheet ID if you use another spreadsheet

```javascript
const CONFIG = {
  secret: 'CHANGE_ME',
  spreadsheetId: '1LmrVATCwGPoDhJIebsHOjpvM35fDnaU_wWZzgov1WOw',
  appointmentsSheet: 'Записи',
  historySheet: 'История клиентов',
};

const APPOINTMENT_HEADERS = [
  'ID заявки',
  'Имя',
  'Телефон',
  'Услуга',
  'Врач',
  'Дата',
  'Время',
  'Статус',
  'Комментарий',
  'Оценка',
  'Отзыв',
  'Создана',
  'Обновлена',
  'Подтверждена'
];

const HISTORY_HEADERS = [
  'Дата события',
  'ID клиента',
  'Имя',
  'Телефон',
  'ID заявки',
  'Событие',
  'Старый статус',
  'Новый статус',
  'Детали',
  'Администратор'
];

function doGet() {
  return jsonResponse_({
    ok: true,
    service: 'AVIDENTIKA Google Sheets webhook'
  });
}

function doPost(e) {
  const lock = LockService.getScriptLock();

  try {
    lock.waitLock(10000);

    const raw = e && e.postData && e.postData.contents ? e.postData.contents : '{}';
    const payload = JSON.parse(raw);

    if (CONFIG.secret && payload.webhook_secret !== CONFIG.secret) {
      return jsonResponse_({
        ok: false,
        error: 'unauthorized'
      });
    }

    const ss = SpreadsheetApp.openById(CONFIG.spreadsheetId);
    const record = payload.record || {};
    const type = payload.type || 'appointment';
    const event = payload.event || '';
    const details = payload.details || '';

    if (type === 'appointment') {
      syncAppointment_(ss, record, event, details);
      appendHistory_(ss, record, event, details);
    } else if (type === 'history') {
      appendHistory_(ss, record, event, details);
    } else {
      return jsonResponse_({
        ok: false,
        error: 'unsupported_type',
        type: type
      });
    }

    return jsonResponse_({ ok: true });
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    return jsonResponse_({
      ok: false,
      error: String(error && error.message ? error.message : error)
    });
  } finally {
    if (lock.hasLock()) {
      lock.releaseLock();
    }
  }
}

function syncAppointment_(ss, record, event, details) {
  const sheet = ensureSheet_(ss, CONFIG.appointmentsSheet, APPOINTMENT_HEADERS);

  const publicId = String(record.public_id || '');
  if (!/^A-[A-F0-9]{8}$/.test(publicId)) {
    throw new Error('Invalid appointment ID: ' + publicId);
  }

  const row = [
    publicId,
    record.patient_name || '',
    record.phone || '',
    record.service || record.confirmed_service || '',
    record.doctor || record.confirmed_doctor || '',
    record.preferred_date || record.confirmed_date || '',
    record.preferred_time || record.confirmed_time || '',
    record.status || '',
    record.comment || record.confirmation_comment || details || '',
    record.rating || '',
    record.review || '',
    record.created_at || new Date(),
    record.updated_at || '',
    record.confirmed_at || record.confirmed_start_at || ''
  ].map(safeCell_);

  const lastRow = sheet.getLastRow();
  let targetRow = lastRow + 1;

  if (lastRow > 1) {
    const ids = sheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues().flat();
    const index = ids.indexOf(publicId);
    if (index >= 0) {
      targetRow = index + 2;
    }
  }

  sheet.getRange(targetRow, 1, 1, APPOINTMENT_HEADERS.length).setValues([row]);
}

function appendHistory_(ss, record, event, details) {
  const sheet = ensureSheet_(ss, CONFIG.historySheet, HISTORY_HEADERS);

  const publicId = String(record.public_id || '');
  if (!/^[AS]-[A-F0-9]{8}$/.test(publicId)) {
    throw new Error('Invalid request ID: ' + publicId);
  }

  const row = [
    new Date(),
    record.user_id || record.profile_id || '',
    record.patient_name || '',
    record.phone || '',
    publicId,
    event || '',
    record.old_status || '',
    record.status || '',
    details || record.question || record.comment || '',
    record.admin_name || ''
  ].map(safeCell_);

  sheet.getRange(sheet.getLastRow() + 1, 1, 1, HISTORY_HEADERS.length).setValues([row]);
}

function ensureSheet_(ss, name, headers) {
  let sheet = ss.getSheetByName(name);

  if (!sheet) {
    sheet = ss.insertSheet(name);
  }

  const lastColumn = Math.max(sheet.getLastColumn(), headers.length);
  const currentHeaders = sheet.getRange(1, 1, 1, headers.length).getDisplayValues()[0];

  if (currentHeaders.join('\u0000') !== headers.join('\u0000')) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }

  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, headers.length)
    .setBackground('#0B1F33')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold');

  sheet.autoResizeColumns(1, lastColumn);
  return sheet;
}

function clearAvidentikaSheets() {
  const ss = SpreadsheetApp.openById(CONFIG.spreadsheetId);
  [CONFIG.appointmentsSheet, CONFIG.historySheet].forEach(function(name) {
    const sheet = ss.getSheetByName(name);
    if (!sheet) return;

    const lastRow = sheet.getLastRow();
    const lastColumn = sheet.getLastColumn();
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow - 1, lastColumn).clearContent();
    }
  });
}

function safeCell_(value) {
  if (value === null || value === undefined) return '';
  if (typeof value !== 'string') return value;
  return /^[=+\-@]/.test(value) ? "'" + value : value;
}

function jsonResponse_(body) {
  return ContentService
    .createTextOutput(JSON.stringify(body))
    .setMimeType(ContentService.MimeType.JSON);
}
```

## Deploy

1. `Deploy -> New deployment` or `Deploy -> Manage deployments -> Edit`
2. Type: `Web app`
3. Execute as: `Me`
4. Who has access: `Anyone`
5. Use `Version -> New version -> Deploy` after every script change
6. Copy the Web App URL into `.env`

## Environment

Add to `.env`:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_WEB_APP_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
GOOGLE_SHEETS_WEBHOOK_SECRET=CHANGE_ME
```

Never commit `.env` to Git.

## Test

```bash
WEBAPP=$(grep '^GOOGLE_SHEETS_WEB_APP_URL=' .env | cut -d= -f2-)
SECRET=$(grep '^GOOGLE_SHEETS_WEBHOOK_SECRET=' .env | cut -d= -f2-)

curl -sS -L \
  -H "Content-Type: application/json" \
  -d "{\"webhook_secret\":\"$SECRET\",\"type\":\"appointment\",\"event\":\"Тест\",\"details\":\"Проверка curl\",\"record\":{\"public_id\":\"A-ABCDEF12\",\"source\":\"website\",\"status\":\"new\",\"patient_name\":\"Тест Клиент\",\"phone\":\"+380995614849\",\"telegram_username\":\"test_user\",\"service\":\"Консультация\",\"preferred_date\":\"25.06.2026\",\"preferred_time\":\"14:00\",\"doctor\":\"Не выбран\",\"comment\":\"Тест\"}}" \
  "$WEBAPP"
```

Expected response:

```json
{"ok":true}
```

A row should appear in `Записи` and a history row should appear in `История клиентов`.

## Reset data

Supabase clean reset for appointments, requests, profiles, conversations and website messages:

```sql
truncate table
  public.web_messages,
  public.conversations,
  public.appointments,
  public.support_requests,
  public.profiles
restart identity cascade;
```

This keeps `knowledge_documents` intact so the AI assistant keeps its knowledge base.

To clear Google Sheets rows while keeping headers, run the Apps Script function:

```javascript
clearAvidentikaSheets()
```
