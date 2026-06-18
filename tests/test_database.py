import asyncio
from types import SimpleNamespace

import pytest

from app.models.schemas import AppointmentInput
from app.services.supabase_service import DatabaseError, SupabaseService


class FakeBuilder:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.payload = None
        self.mutation = False

    def insert(self, payload): self.mutation = True; self.payload = payload; self.client.last_payload = payload; return self
    def update(self, payload): self.mutation = True; self.payload = payload; self.client.last_payload = payload; return self
    def upsert(self, payload, **kwargs): self.mutation = True; self.payload = payload; self.client.last_payload = payload; return self
    def select(self, *args): return self
    def limit(self, *args):
        if self.mutation:
            raise AssertionError("limit() must not be used after insert/update/upsert")
        return self
    def eq(self, *args): return self
    def is_(self, *args): return self
    def gt(self, *args): return self
    def gte(self, *args): return self
    def lt(self, *args): return self
    def lte(self, *args): return self
    def order(self, *args): return self
    def execute(self):
        if self.client.fail:
            raise RuntimeError("offline")
        if self.table in self.client.table_data:
            return SimpleNamespace(data=self.client.table_data[self.table])
        data = {"id": "db-id", **(self.payload or {})}
        return SimpleNamespace(data=[data])


class FakeClient:
    def __init__(self, fail=False, table_data=None):
        self.fail, self.last_payload = fail, None
        self.table_data = table_data or {}
    def table(self, name): return FakeBuilder(self, name)


def test_supabase_layer_is_mockable() -> None:
    service = SupabaseService(client=FakeClient())
    user = SimpleNamespace(id=12, username="test", first_name="Ivan", last_name=None)
    result = asyncio.run(service.upsert_profile(user, "uk"))
    assert result["telegram_user_id"] == 12


def test_creates_appointment_with_public_id() -> None:
    client = FakeClient()
    service = SupabaseService(client=client)
    value = AppointmentInput("Іван", "+380671234567", "Діагностика")
    result = asyncio.run(service.create_appointment("profile-id", value))
    assert result["public_id"].startswith("A-")
    assert result["status"] == "new"


def test_changes_status() -> None:
    service = SupabaseService(client=FakeClient())
    result = asyncio.run(service.update_request_status("appointment", "A-1234ABCD", "closed", 99))
    assert result["status"] == "closed"
    assert result["assigned_admin_telegram_id"] == 99
    assert result["closed_at"]


def test_gets_client_notification_target_from_profile() -> None:
    service = SupabaseService(client=FakeClient(table_data={
        "profiles": [{"telegram_user_id": 321, "preferred_language": "uk"}],
    }))
    result = asyncio.run(service.get_profile_notification_target("profile-id"))
    assert result == {"telegram_user_id": 321, "preferred_language": "uk"}


def test_confirms_appointment_with_structured_details() -> None:
    client = FakeClient()
    service = SupabaseService(client=client)
    result = asyncio.run(service.confirm_appointment("A-1234ABCD", {
        "confirmed_date": "25.06.2026",
        "confirmed_time": "15:30",
        "confirmed_service": "Лікування каналів",
        "confirmed_doctor": "Амін",
        "confirmation_comment": "Не запізнюватися",
        "confirmed_start_at": "2026-06-25T12:30:00+00:00",
    }, 99))
    assert result["status"] == "confirmed"
    assert result["confirmed_doctor"] == "Амін"
    assert result["confirmed_at"]


def test_client_can_confirm_cancel_or_request_reschedule() -> None:
    service = SupabaseService(client=FakeClient())
    confirmed = asyncio.run(service.set_visit_response("A-1234ABCD", "confirmed"))
    assert confirmed["client_confirmation_status"] == "confirmed"
    moved = asyncio.run(service.set_visit_response("A-1234ABCD", "reschedule_requested"))
    assert moved["status"] == "in_progress"
    cancelled = asyncio.run(service.set_visit_response("A-1234ABCD", "cancelled"))
    assert cancelled["status"] == "cancelled"


def test_saves_rating() -> None:
    service = SupabaseService(client=FakeClient())
    result = asyncio.run(service.save_rating("A-1234ABCD", 5))
    assert result["rating"] == 5


def test_wraps_supabase_error() -> None:
    service = SupabaseService(client=FakeClient(fail=True))
    with pytest.raises(DatabaseError):
        asyncio.run(service.create_appointment("x", AppointmentInput("Іван", "+380671234567", "Огляд")))
