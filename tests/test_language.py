from app.utils.language import detect_language


def test_detects_ukrainian() -> None:
    assert detect_language("Яка ціна лікування зубів?") == "uk"


def test_detects_russian() -> None:
    assert detect_language("Какая цена лечения зубов?") == "ru"


def test_defaults_to_ukrainian() -> None:
    assert detect_language("Hello 123") == "uk"
