from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class AppointmentInput:
    patient_name: str
    phone: str
    service: str
    preferred_date: str | None = None
    preferred_time: str | None = None
    comment: str | None = None

    def to_record(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "status": "new", **asdict(self)}


@dataclass(slots=True)
class SupportInput:
    patient_name: str
    phone: str
    question: str

    def to_record(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "status": "new", **asdict(self)}


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    content: str
    source_url: str
    page_title: str
    similarity: float


@dataclass(frozen=True, slots=True)
class AIAnswer:
    text: str
    source_url: str | None = None
