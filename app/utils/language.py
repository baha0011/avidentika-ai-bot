import re

UK_CHARS = set("іїєґІЇЄҐ")
RU_CHARS = set("ыэъёЫЭЪЁ")
UA_WORDS = {"будь", "ласка", "ціна", "лікар", "послуга", "записатися", "дякую", "потрібно", "зубів"}
RU_WORDS = {"пожалуйста", "цена", "врач", "услуга", "записаться", "спасибо", "нужно", "зубов", "можно", "поставить", "пломба", "пломбу", "пломбы", "лечить", "лечение", "делаете", "сколько", "стоит"}


def detect_language(text: str) -> str:
    if any(char in UK_CHARS for char in text):
        return "uk"
    if any(char in RU_CHARS for char in text):
        return "ru"
    words = set(re.findall(r"[а-яіїєґё]+", text.lower()))
    ru_score, uk_score = len(words & RU_WORDS), len(words & UA_WORDS)
    return "ru" if ru_score > uk_score else "uk"
