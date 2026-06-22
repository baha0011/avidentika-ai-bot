from __future__ import annotations


def detect_language(text: str, requested: str = "auto") -> str:
    if requested in {"ru", "uk"}:
        return requested
    lowered = text.lower()
    if any(char in lowered for char in "іїєґ") or any(word in lowered for word in ("будь ласка", "лікар", "послуга")):
        return "uk"
    return "ru"


def quick_actions(language: str) -> list[str]:
    if language == "uk":
        return ["Записатися на прийом", "Поставити питання", "Зв’язатися з адміністратором", "Послуги", "Лікарі", "Ціни", "Контакти"]
    return ["Записаться на приём", "Задать вопрос", "Связаться с администратором", "Услуги", "Врачи", "Цены", "Контакты"]
