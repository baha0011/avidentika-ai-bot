from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.phone import normalize_ua_phone

Language = Literal["ru", "uk", "auto"]


class SessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=120)
    message: str = Field(min_length=1, max_length=1500)
    language: Language = "auto"


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    quick_actions: list[str] = Field(default_factory=list)


class AppointmentCreate(BaseModel):
    session_id: str = Field(min_length=8, max_length=120)
    patient_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=30)
    telegram_username: str | None = Field(default=None, max_length=64)
    service: str = Field(min_length=1, max_length=200)
    preferred_date: str | None = Field(default=None, max_length=80)
    preferred_time: str | None = Field(default=None, max_length=80)
    doctor: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=500)
    contact_method: str | None = Field(default="phone", max_length=40)
    created_from_url: str | None = Field(default=None, max_length=500)
    language: Language = "auto"

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        normalized = normalize_ua_phone(value)
        if not normalized:
            raise ValueError("Неверный украинский номер телефона")
        return normalized


class AppointmentResponse(BaseModel):
    public_id: str
    status: str
    message: str


class SupportCreate(BaseModel):
    session_id: str = Field(min_length=8, max_length=120)
    patient_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=30)
    telegram_username: str | None = Field(default=None, max_length=64)
    question: str = Field(min_length=3, max_length=1000)
    contact_method: str | None = Field(default="phone", max_length=40)
    created_from_url: str | None = Field(default=None, max_length=500)
    language: Language = "auto"

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        normalized = normalize_ua_phone(value)
        if not normalized:
            raise ValueError("Неверный украинский номер телефона")
        return normalized


class SupportResponse(BaseModel):
    public_id: str
    status: str
    message: str
