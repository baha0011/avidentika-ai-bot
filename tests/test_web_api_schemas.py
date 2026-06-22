import pytest
from pydantic import ValidationError

from app.api.helpers import detect_language, quick_actions
from app.api.schemas import AppointmentCreate, ChatRequest, SupportCreate


def test_chat_request_accepts_valid_payload() -> None:
    payload = ChatRequest(session_id="web-test-123", message="Какие услуги есть?", language="ru")
    assert payload.language == "ru"


def test_appointment_phone_is_normalized() -> None:
    payload = AppointmentCreate(
        session_id="web-test-123",
        patient_name="Иван",
        phone="067 123-45-67",
        service="Консультация",
    )
    assert payload.phone == "+380671234567"


def test_support_rejects_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        SupportCreate(
            session_id="web-test-123",
            patient_name="Иван",
            phone="+48123123123",
            question="Вопрос администратору",
        )


def test_detect_language_ukrainian() -> None:
    assert detect_language("Підкажіть, будь ласка, графік лікаря") == "uk"


def test_quick_actions_are_public_labels_only() -> None:
    text = " ".join(quick_actions("ru")).lower()
    assert "пароль" not in text
    assert "секрет" not in text
