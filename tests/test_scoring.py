from market_analyst.services.scoring import extract_rating_from_text, normalize_rating, parse_json_object


def test_normalize_rating_uses_one_to_one_hundred_contract() -> None:
    assert normalize_rating(0) == 1
    assert normalize_rating(101) == 100
    assert normalize_rating("72.4/100") == 72
    assert normalize_rating(True) is None


def test_extract_rating_from_json_and_labelled_text() -> None:
    assert extract_rating_from_text('{"technical_rating": 83}') == 83
    assert extract_rating_from_text("Final rating: 64 out of 100") == 64
    assert parse_json_object('```json\n{"rating": 55}\n```') == {"rating": 55}
