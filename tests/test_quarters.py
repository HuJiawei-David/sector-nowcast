from nowcast.quarters import Quarter, d_clean, qrange, yoy_clean

US = (Quarter(2020, 1), Quarter(2021, 4))
TCOM = (Quarter(2020, 1), Quarter(2022, 4))


def test_arithmetic():
    q = Quarter.parse("2023Q1")
    assert str(q - 1) == "2022Q4" and str(q + 4) == "2024Q1"
    assert len(qrange(Quarter.parse("2023Q2"), Quarter.parse("2026Q3"))) == 14


def test_first_clean_values_match_claude_md():
    assert not yoy_clean(Quarter(2022, 4), US) and yoy_clean(Quarter(2023, 1), US)
    assert not d_clean(Quarter(2023, 1), US) and d_clean(Quarter(2023, 2), US)
    assert not d_clean(Quarter(2024, 1), TCOM) and d_clean(Quarter(2024, 2), TCOM)


def test_bad_label_fails_loudly():
    import pytest
    with pytest.raises(ValueError):
        Quarter.parse("2023-Q1")
