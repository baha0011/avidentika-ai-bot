from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")


def parse_appointment_datetime(date_text: str, time_text: str) -> datetime:
    value = datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%d.%m.%Y %H:%M")
    return value.replace(tzinfo=KYIV)


def utc_day_bounds(day: datetime) -> tuple[str, str]:
    local_start = datetime.combine(day.date(), time.min, tzinfo=KYIV)
    local_end = datetime.combine(day.date(), time.max, tzinfo=KYIV)
    return local_start.astimezone(UTC).isoformat(), local_end.astimezone(UTC).isoformat()
