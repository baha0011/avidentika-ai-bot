from datetime import UTC, datetime

from app.utils.datetime_utils import parse_appointment_datetime, utc_day_bounds


def test_parses_kyiv_appointment_datetime() -> None:
    value = parse_appointment_datetime("25.06.2026", "15:30")
    assert value.hour == 15
    assert value.tzinfo is not None


def test_utc_day_bounds_are_ordered() -> None:
    start, end = utc_day_bounds(datetime(2026, 6, 25, tzinfo=UTC))
    assert start < end
