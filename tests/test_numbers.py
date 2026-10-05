import pytest

from finx.numbers import NOTE_REF, detect_locale, parse_number


def test_detect_locale():
    assert detect_locale(["1.777.796", "230.062", "(45.529)"]) == "id"
    assert detect_locale(["4,163,401,077", "(5,108,137)"]) == "en"


@pytest.mark.parametrize("tok,loc,exp", [
    ("1.777.796", "id", 1777796.0),
    ("(45.529)", "id", -45529.0),
    ("0,00060", "id", 0.0006),
    ("(64,37)", "id", -64.37),
    ("4,163,401,077", "en", 4163401077.0),
    ("(5,108,137)", "en", -5108137.0),
    ("0.77", "en", 0.77),
    ("−", "id", 0.0),
    ("-", "en", 0.0),
    ("-12.000", "id", -12000.0),
])
def test_parse_number(tok, loc, exp):
    assert parse_number(tok, loc) == pytest.approx(exp)


@pytest.mark.parametrize("tok", ["Kas", "2024)", "(Catatan", "", "Rp", "1.2.3,4,5"])
def test_parse_number_rejects_non_numbers(tok):
    assert parse_number(tok, "id") is None


@pytest.mark.parametrize("tok", ["4", "21a", "6,37", "2b,2g,4,38,", "8,", "2ad,2aj,29,48"])
def test_note_ref_matches_note_tokens(tok):
    assert NOTE_REF.fullmatch(tok)


@pytest.mark.parametrize("tok", ["272.991", "1.000", "Kas", "1.777.796"])
def test_note_ref_rejects_values(tok):
    assert not NOTE_REF.fullmatch(tok)
