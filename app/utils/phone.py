import re


def normalize_ua_phone(value: str) -> str | None:
    """Normalize Ukrainian phone numbers to +380XXXXXXXXX.

    Accepted examples:
    - +380 99 561 48 49
    - +38 (099)561-67-34
    - 099 561 48 49
    - 380995614849
    - 00380995614849
    """
    if not value:
        return None

    digits = re.sub(r"\D", "", str(value))

    if digits.startswith("00380") and len(digits) == 14:
        digits = digits[2:]
    elif digits.startswith("38") and len(digits) == 12:
        pass
    elif digits.startswith("0") and len(digits) == 10:
        digits = "38" + digits
    elif digits.startswith("80") and len(digits) == 11:
        digits = "3" + digits
    else:
        return None

    number = "+" + digits
    if not re.fullmatch(r"\+380\d{9}", number):
        return None
    return number


def mask_phone(value: str) -> str:
    normalized = normalize_ua_phone(value)
    return f"+380******{normalized[-3:]}" if normalized else "***"
