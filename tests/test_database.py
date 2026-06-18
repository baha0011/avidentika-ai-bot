import asyncio
from types import SimpleNamespace

import pytest

from app.models.schemas import AppointmentInput
from app.services.supabase_service import DatabaseError, SupabaseService


class FakeBuilder:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.payload = None

    def insert(self, payload): self.payload = payload; self.client.last_payload = payload; return self
    def update(self, payload): self.payload = payload; self.client.last_payload = payload; return self
    def upsert(self, payload, **kwargs): self.payload = payload; self.client.last_payload = payload; return self
    def select(self, *args): return self
    def limit(self, *args): return self
    def eq(self, *args): return self
    def execute(self):
        if self.client.fail:
            raise RuntimeError("offline")
        data = {"id": "db-id", **(self.payload or {})}
        return SimpleNamespace(data=[data])


class FakeClient:
    def __init__(self, fail=False): self.fail, self.last_payload = fail, None
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


def test_wraps_supabase_error() -> None:
    service = SupabaseService(client=FakeClient(fail=True))
    with pytest.raises(DatabaseError):
        asyncio.run(service.create_appointment("x", AppointmentInput("Іван", "+380671234567", "Огляд")))
