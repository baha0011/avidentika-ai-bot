from app.utils.phone import mask_phone, normalize_ua_phone


def test_normalizes_local_ua_phone() -> None:
    assert normalize_ua_phone("067 123-45-67") == "+380671234567"


def test_accepts_international_ua_phone() -> None:
    assert normalize_ua_phone("+380 (44) 123-45-67") == "+380441234567"


def test_accepts_flexible_website_phone_formats() -> None:
    assert normalize_ua_phone("+380 99 561 48 49") == "+380995614849"
    assert normalize_ua_phone("+38 (099)561-67-34") == "+380995616734"
    assert normalize_ua_phone("099.561.48.49") == "+380995614849"
    assert normalize_ua_phone("00380 99 561 48 49") == "+380995614849"
    assert normalize_ua_phone("80 99 561 48 49") == "+380995614849"


def test_rejects_invalid_phone() -> None:
    assert normalize_ua_phone("+48123123123") is None
    assert normalize_ua_phone("067123") is None


def test_masks_phone() -> None:
    assert mask_phone("0671234567") == "+380******567"
