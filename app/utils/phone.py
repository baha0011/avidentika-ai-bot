import re

def normalize_ua_phone(value: str) -> str | None:
    cleaned = re.sub(r"[\s()\-]", "", value.strip())
    if cleaned.startswith("+380") and len(cleaned) == 13:
        number = cleaned
    elif cleaned.startswith("380") and len(cleaned) == 12:
        number = "+" + cleaned
    elif cleaned.startswith("0") and len(cleaned) == 10:
        number = "+38" + cleaned
    else:
        return None
    if not re.fullmatch(r"\+380\d{9}", number):
        return None
    return number


def mask_phone(value: str) -> str:
    normalized = normalize_ua_phone(value)
    return f"+380******{normalized[-3:]}" if normalized else "***"
