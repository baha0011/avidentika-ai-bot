# Google Sheets webhook

The bot mirrors appointments and support history to Google Sheets through an Apps Script Web App.

## Sheets

Create a spreadsheet with two sheets:

- `Записи`
- `История`

The script creates headers automatically on the first write.

## Apps Script

Open Extensions -> Apps Script and paste:

```javascript
const CONFIG = {
  secret: 'CHANGE_ME',
  appointmentsSheet: 'Записи',
  historySheet: 'История',
};

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents || '{}');
    if (CONFIG.secret && payload.webhook_secret !== CONFIG.secret) {
      return json({ ok: false, error: 'forbidden' });
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const record = payload.record || {};
    const type = payload.type || 'appointment';
    const event = payload.event || '';
    const details = payload.details || '';

    if (type === 'appointment') {
      appendAppointment(ss, record, event, details);
    } else {
      appendHistory(ss, record, event, details);
    }

    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function appendAppointment(ss, record, event, details) {
  const sheet = getSheet(ss, CONFIG.appointmentsSheet);
  ensureHeader(sheet, [
    'created_at', 'event', 'public_id', 'source', 'status', 'patient_name',
    'phone', 'telegram_username', 'service', 'preferred_date', 'preferred_time',
    'doctor', 'confirmed_date', 'confirmed_time', 'confirmed_doctor', 'comment', 'details'
  ]);
  sheet.appendRow([
    new Date(),
    event,
    record.public_id || '',
    record.source || 'telegram',
    record.status || '',
    record.patient_name || '',
    record.phone || '',
    record.telegram_username || '',
    record.service || record.confirmed_service || '',
    record.preferred_date || '',
    record.preferred_time || '',
    record.doctor || '',
    record.confirmed_date || '',
    record.confirmed_time || '',
    record.confirmed_doctor || '',
    record.comment || record.confirmation_comment || '',
    details,
  ]);
}

function appendHistory(ss, record, event, details) {
  const sheet = getSheet(ss, CONFIG.historySheet);
  ensureHeader(sheet, [
    'created_at', 'event', 'public_id', 'source', 'status', 'patient_name',
    'phone', 'telegram_username', 'question', 'details'
  ]);
  sheet.appendRow([
    new Date(),
    event,
    record.public_id || '',
    record.source || 'telegram',
    record.status || '',
    record.patient_name || '',
    record.phone || '',
    record.telegram_username || '',
    record.question || '',
    details,
  ]);
}

function getSheet(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function ensureHeader(sheet, headers) {
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }
}

function json(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
```

Deploy:

1. Deploy -> New deployment
2. Type: Web app
3. Execute as: Me
4. Who has access: Anyone
5. Copy the Web App URL

## Bot env

Add to `.env`:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_WEB_APP_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
GOOGLE_SHEETS_WEBHOOK_SECRET=CHANGE_ME
```

The value in `GOOGLE_SHEETS_WEBHOOK_SECRET` must be the same as `CONFIG.secret` in Apps Script.

## Test

Restart the bot and API, then create a website appointment. A row should appear in `Записи`.
